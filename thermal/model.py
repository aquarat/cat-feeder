#!/usr/bin/env python3
"""Stdlib finite-volume thermal screening; SI internally except plan geometry (mm)."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Parameters:
    dx_mm: float = 2.0
    outer_mm: float = 137.0
    inner_mm: float = 62.0
    angle_deg: float = 26.0
    corner_mm: float = 5.0
    cap_center_mm: float = 105.0
    cap_width_mm: float = 41.28
    rectangles_mm: tuple = ()  # optional (centre x, centre y, radial size, tangential size)
    cap_thickness: float = 0.003
    aluminium_k: float = 200.0
    floor: float = 0.0012
    petg_k: float = 0.2
    volume: float = 40e-6
    depth: float = 0.0  # zero: calculate uniform depth from volume / grid area
    food_k: float = 0.5
    lateral_multiplier: float = 1.0
    rho: float = 1000.0
    cp: float = 3800.0
    contact_r: float = 0.0  # m2 K/W; additional to floor, food, aluminium
    top_h: float = 5.0
    side_h: float = 0.0
    deck_thickness: float = 0.018
    deck_k: float = 0.06
    ambient: float = 25.0
    underside: float = 30.0
    cold: float = 0.0
    full_plate: bool = False
    deck_enabled: bool = True
    half_food_resistance: bool = True


def rectangles(p):
    return p.rectangles_mm or ((p.cap_center_mm, 0.0, p.cap_width_mm, p.cap_width_mm),)


def rectangle_bounds(p):
    return [(x-w/2, x+w/2, y-h/2, y+h/2) for x,y,w,h in rectangles(p)]


def union_area(bounds, clip=None):
    """Exact axis-aligned rectangle union area by x slabs and merged y intervals."""
    boxes = []
    for x0,x1,y0,y1 in bounds:
        if clip is not None:
            x0,x1 = max(x0,clip[0]),min(x1,clip[1])
            y0,y1 = max(y0,clip[2]),min(y1,clip[3])
        if x1>x0 and y1>y0:
            boxes.append((x0,x1,y0,y1))
    xs=sorted({x for box in boxes for x in box[:2]})
    area=0.0
    for lo,hi in zip(xs,xs[1:]):
        intervals=sorted((y0,y1) for x0,x1,y0,y1 in boxes if x0<hi and x1>lo)
        length=0.0
        end=-math.inf
        for y0,y1 in intervals:
            length += max(0.0,y1-max(y0,end))
            end=max(end,y1)
        area += (hi-lo)*length
    return area


def footprint_fit(p, clearance=0.0):
    """Analytic containment in one +/-15 degree site; no discretisation.

    For these centred, mirror-symmetric footprints the closest adjacent-site
    corner pair has separation twice the minimum normal half-sector margin.
    A negative margin denotes overlap for the candidates considered here.
    """
    a=math.pi/12
    margin=min((x-w/2-clearance)*math.sin(a)-(abs(y)+h/2+clearance)*math.cos(a)
               for x,y,w,h in rectangles(p))
    outer=max(math.hypot(x+w/2+clearance,abs(y)+h/2+clearance)
              for x,y,w,h in rectangles(p))
    return dict(half_sector_normal_margin_mm=margin,
                adjacent_site_gap_mm=2*margin,
                twelve_sites_nonoverlap=margin>=0,
                outer_corner_radius_mm=outer,
                inside_146mm_deck=outer<=146,
                inside_150mm_housing=outer<=150)


def footprint_variants(p):
    return [('square_41.28_r105',p),
            ('rectangle_60x40_r105',replace(p,rectangles_mm=((105,0,60,40),))),
            ('rectangle_60x40_r107',replace(p,rectangles_mm=((107,0,60,40),))),
            ('rectangle_70x30_r100',replace(p,rectangles_mm=((100,0,70,30),))),
            ('two_squares_30_r82_r115',replace(p,rectangles_mm=((82,0,30,30),(115,0,30,30)))),
            ('full_plate_reference',replace(p,full_plate=True))]


def segment_distance(x, y, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    u = max(0.0, min(1.0, ((x-a[0])*vx + (y-a[1])*vy)/(vx*vx+vy*vy)))
    return math.hypot(x-a[0]-u*vx, y-a[1]-u*vy)


def inside(x, y, p):
    """Exact circular/line erosion by corner radius, then circular dilation.

    Matches CAD offset(r=5) offset(delta=-5) of disk intersected with wedge
    and x>=62, apart from CAD circle tessellation; ignores 3D bottom fillet.
    """
    a = math.radians(p.angle_deg/2)
    r, R, xi = p.corner_mm, p.outer_mm-p.corner_mm, p.inner_mm+p.corner_mm
    if x < p.inner_mm or x*x+y*y > p.outer_mm**2 or abs(y) > x*math.tan(a):
        return False
    if x >= xi and x*x+y*y <= R*R and abs(y) <= x*math.tan(a)-r/math.cos(a):
        return True
    yi = xi*math.tan(a)-r/math.cos(a)
    xt = r*math.sin(a)+math.cos(a)*math.sqrt(R*R-r*r)
    yt = -r*math.cos(a)+math.sin(a)*math.sqrt(R*R-r*r)
    segments = [((xi,-yi),(xi,yi)), ((xi,yi),(xt,yt)), ((xi,-yi),(xt,-yt))]
    dist = min(segment_distance(x,y,u,v) for u,v in segments)
    if abs(math.atan2(y,x)) <= math.atan2(yt,xt):
        dist = min(dist, abs(math.hypot(x,y)-R))
    return dist <= r+1e-10


class Model:
    def __init__(self, p):
        self.p = p
        d = p.dx_mm
        # Global symmetric cell-centred grid; exposed faces are insulated unless side_h>0.
        self.xy = [(i*d, (j+0.5)*d)
                   for i in range(math.floor(p.inner_mm/d), math.ceil(p.outer_mm/d)+1)
                   for j in range(-math.ceil(p.outer_mm*math.sin(math.radians(p.angle_deg/2))/d),
                                  math.ceil(p.outer_mm*math.sin(math.radians(p.angle_deg/2))/d))
                   if inside(i*d,(j+0.5)*d,p)]
        self.n = len(self.xy)
        self.area_cell = (d/1000)**2
        self.area = self.n*self.area_cell
        self.depth = p.depth or p.volume/self.area
        index = {(round(x/d),round(y/d-0.5)): i for i,(x,y) in enumerate(self.xy)}
        self.edges = []
        faces = [4]*self.n
        for (ix,iy), i in index.items():
            for delta in [(1,0),(0,1)]:
                j = index.get((ix+delta[0],iy+delta[1]))
                if j is not None:
                    self.edges.append((i,j))
                    faces[i] -= 1
                    faces[j] -= 1
        self.g = p.food_k*p.lateral_multiplier*self.depth + p.petg_k*p.floor
        rv = (self.depth/(2*p.food_k)) if p.half_food_resistance else 0
        self.cold_u = 1/(p.floor/p.petg_k + rv + p.contact_r + p.cap_thickness/p.aluminium_k)
        self.deck_u = 1/(p.deck_thickness/p.deck_k+p.floor/p.petg_k+rv) if p.deck_enabled else 0
        self.fraction = []
        bounds=rectangle_bounds(p)
        for x,y in self.xy:
            if p.full_plate:
                fraction = 1.0
            else:
                fraction = union_area(bounds,(x-d/2,x+d/2,y-d/2,y+d/2))/d**2
            assert -1e-12 <= fraction <= 1+1e-12
            self.fraction.append(fraction)
        self.gc = [self.cold_u*self.area_cell*f for f in self.fraction]
        self.gb = [self.deck_u*self.area_cell*(1-f) for f in self.fraction]
        self.ga = [p.top_h*self.area_cell+p.side_h*self.depth*d/1000*f for f in faces]
        self.diag = [self.gc[i]+self.gb[i]+self.ga[i]+(4-faces[i])*self.g for i in range(self.n)]
        self.rhs = [self.gc[i]*p.cold+self.gb[i]*p.underside+self.ga[i]*p.ambient for i in range(self.n)]
        self.capacity = p.rho*p.cp*self.depth*self.area_cell  # food only

    def multiply(self, x, extra=0):
        y = [(v+extra)*t for v,t in zip(self.diag,x)]
        g = self.g
        for i,j in self.edges:
            y[i] -= g*x[j]
            y[j] -= g*x[i]
        return y

    def solve(self, rhs=None, initial=None, extra=0, tolerance=1e-10):
        """Jacobi-preconditioned conjugate gradient; fixed positive boundaries give SPD."""
        b = self.rhs if rhs is None else rhs
        x = [self.p.ambient]*self.n if initial is None else list(initial)
        ax = self.multiply(x,extra)
        r = [v-w for v,w in zip(b,ax)]
        target = tolerance*max(math.sqrt(sum(v*v for v in b)),1e-3)
        z = [v/(d+extra) for v,d in zip(r,self.diag)]
        direction = list(z)
        rz = sum(v*w for v,w in zip(r,z))
        for iteration in range(10000):
            residual = math.sqrt(sum(v*v for v in r))
            if residual < target:
                return x, iteration, residual
            ad = self.multiply(direction,extra)
            alpha = rz/sum(v*w for v,w in zip(direction,ad))
            x = [v+alpha*w for v,w in zip(x,direction)]
            r = [v-alpha*w for v,w in zip(r,ad)]
            z = [v/(d+extra) for v,d in zip(r,self.diag)]
            new_rz = sum(v*w for v,w in zip(r,z))
            beta = new_rz/rz
            direction = [v+beta*w for v,w in zip(z,direction)]
            rz = new_rz
        raise RuntimeError("CG did not converge")

    def stats(self, t):
        p = self.p
        qc = sum(g*(v-p.cold) for g,v in zip(self.gc,t))
        qt = sum(g*(p.ambient-v) for g,v in zip(self.ga,t))
        qb = sum(g*(p.underside-v) for g,v in zip(self.gb,t))
        imax = max(range(self.n),key=t.__getitem__)
        return dict(cells=self.n, area_cm2=self.area*1e4, depth_mm=self.depth*1000,
                    volume_ml=self.area*self.depth*1e6,
                    cap_overlap_cm2=sum(self.fraction)*self.area_cell*1e4,
                    footprint_coverage_fraction=sum(self.fraction)/self.n,
                    mean_C=sum(t)/len(t), min_C=min(t), max_C=max(t),
                    warmest_x_mm=self.xy[imax][0], warmest_y_mm=self.xy[imax][1],
                    fraction_above_4C=sum(v>4 for v in t)/len(t),
                    cold_W=qc, ambient_W=qt, deck_W=qb, balance_W=qt+qb-qc)


def write_csv(path, rows):
    with path.open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def heatmap(path, m, t, title):
    def color(v):
        f = max(0,min(1,v/25))
        return f'rgb({int(255*f)},60,{int(255*(1-f))})'
    # Common 0..25 C scale for direct comparison; coordinates are plan millimetres.
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="650" viewBox="50 -53 100 83">',
             f'<title>{title}</title>', '<rect x="50" y="-53" width="100" height="108" fill="white"/>',
             f'<text x="53" y="-47" font-size="3">{title}</text>',
             '<text x="53" y="-42" font-size="2.5">Thickness-averaged food temperature; x/y in mm</text>']
    d = m.p.dx_mm
    for (x,y),v in zip(m.xy,t):
        lines.append(f'<rect x="{x-d/2:.3f}" y="{-y-d/2:.3f}" width="{d}" height="{d}" fill="{color(v)}"><title>x={x:g}, y={y:g}: {v:.3f} C</title></rect>')
    if not m.p.full_plate:
        for x,y,w,h in rectangles(m.p):
            lines.append(f'<rect x="{x-w/2}" y="{-y-h/2}" width="{w}" height="{h}" fill="none" stroke="black" stroke-width="0.3" stroke-dasharray="1,1"/>')
    for j in range(26):
        lines.append(f'<rect x="{67+j*2.4}" y="35" width="2.5" height="3" fill="{color(j)}"/>')
    lines.extend(['<text x="67" y="42" font-size="3">0 C</text>',
                  '<text x="119" y="42" font-size="3">25 C</text>',
                  f'<text x="60" y="49" font-size="3">mean {sum(t)/len(t):.2f} C; range {min(t):.2f} to {max(t):.2f} C</text>', '</svg>'])
    # Expand viewBox to include legend and statistics.
    lines[0] = lines[0].replace('100 83','100 108')
    path.write_text('\n'.join(lines))


def checks():
    # Overlap, nesting, duplicate and clipped rectangles must never double-count.
    boxes=[(0,2,0,2),(1,3,1,3),(0,2,0,2),(.5,1.5,.5,1.5)]
    assert union_area(boxes)==7
    assert union_area(boxes,(1,2,1,2))==1
    assert union_area(boxes,(4,5,4,5))==0
    # Real overlapping cold patches give exactly the same field as their union.
    single=Model(Parameters(rectangles_mm=((100,0,60,30),)))
    overlap=Model(Parameters(rectangles_mm=((90,0,40,30),(110,0,40,30))))
    assert single.fraction==overlap.fraction
    fits={name:footprint_fit(param) for name,param in footprint_variants(Parameters()) if not param.full_plate}
    assert all(v['twelve_sites_nonoverlap'] for v in fits.values())
    assert not footprint_fit(Parameters(rectangles_mm=((105,0,60,40),)),.3)['twelve_sites_nonoverlap']
    assert footprint_fit(Parameters(rectangles_mm=((107,0,60,40),)),.3)['twelve_sites_nonoverlap']
    p = Parameters(dx_mm=2)
    m = Model(replace(p,ambient=7,underside=7,cold=7))
    t,_,_ = m.solve(initial=[22]*m.n)
    uniform_error=max(abs(v-7) for v in t)
    assert uniform_error < 1e-7
    # Isolated food: no cap or boundary loads. One implicit step conserves energy.
    m = Model(replace(p,top_h=0,deck_enabled=False,cap_center_mm=1000))
    t0 = [4+0.05*x+0.1*y for x,y in m.xy]
    extra=m.capacity/60
    t,_,_=m.solve(rhs=[extra*v for v in t0],initial=t0,extra=extra)
    isolated_energy_error_J=abs(sum(t)-sum(t0))*m.capacity
    assert isolated_energy_error_J < 1e-7
    # Full plate is a spatially uniform resistor network with an analytic answer.
    m=Model(replace(p,full_plate=True))
    expected=(m.cold_u*p.cold+p.top_h*p.ambient)/(m.cold_u+p.top_h)
    t,_,_=m.solve()
    analytic_error=max(abs(v-expected) for v in t)
    assert analytic_error < 1e-7
    # Arbitrary transient step: boundary energy equals change in stored energy.
    m=Model(p)
    t0=[4]*m.n
    t,_,_=m.solve(rhs=[b+m.capacity/60*v for b,v in zip(m.rhs,t0)],initial=t0,extra=m.capacity/60)
    balance_error=abs(m.stats(t)['balance_W']-m.capacity*sum(v-w for v,w in zip(t,t0))/60)
    assert balance_error < 1e-8
    return dict(uniform_equilibrium_max_error_C=uniform_error,
                rectangle_union_checks_passed=True,
                twelve_site_fit_checks_passed=True,
                isolated_step_energy_error_J=isolated_energy_error_J,
                full_plate_analytic_max_error_C=analytic_error,
                transient_energy_balance_error_W=balance_error)


def compare_footprints(out, p):
    """Steady comparisons only: keep the extra runtime small."""
    shapes=footprint_variants(p)
    environments=[('nominal',dict(ambient=25,underside=30,top_h=5)),
                  ('sheltered_top10_base30',dict(ambient=10,underside=30,top_h=5)),
                  ('low_h1_top25_base30',dict(ambient=25,underside=30,top_h=1))]
    rows=[]
    convergence=[]
    parameters={}
    fits=[]
    for name,param in shapes:
        if not param.full_plate:
            fit=dict(footprint=name,rectangle_union_area_cm2=union_area(rectangle_bounds(param))/100,
                     rectangles=json.dumps(rectangles(param)),**footprint_fit(param))
            fit.update({f'pocket_0.3mm_{k}':v for k,v in footprint_fit(param,.3).items()})
            fits.append(fit)
        for environment,change in environments:
            case=replace(param,**change)
            parameters[f'{name}__{environment}']=asdict(case)
            m=Model(case)
            t,it,res=m.solve()
            row=dict(footprint=name,environment=environment,**m.stats(t),iterations=it,residual_l2_W=res)
            assert abs(row['balance_W'])<1e-7
            assert min(t)>=case.cold-1e-7 and max(t)<=max(case.ambient,case.underside)+1e-7
            rows.append(row)
            convergence.append(dict(footprint=name,environment=environment,dx_mm=case.dx_mm,**m.stats(t)))
            if environment=='nominal':
                heatmap(out/f'{name}_nominal.svg',m,t,name.replace('_',' '))
            # Refine steady comparisons, without repeating transient simulations.
            m=Model(replace(case,dx_mm=1))
            t,_,_=m.solve()
            convergence.append(dict(footprint=name,environment=environment,dx_mm=1,**m.stats(t)))
            if name=='rectangle_60x40_r105' and environment=='low_h1_top25_base30':
                # This candidate is near 4 C, so check a finer grid before interpreting it.
                m=Model(replace(case,dx_mm=.5))
                t,_,_=m.solve()
                convergence.append(dict(footprint=name,environment=environment,dx_mm=.5,**m.stats(t)))
    write_csv(out/'footprint_comparison.csv',rows)
    write_csv(out/'footprint_fit.csv',fits)
    write_csv(out/'footprint_grid_convergence.csv',convergence)
    return dict(parameters=parameters,steady=rows,fit=fits,grid_convergence=convergence)


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    p=Parameters()
    cases=[('local_baseline',p), ('full_plate_reference',replace(p,full_plate=True))]
    changes=[('top_h_1',dict(top_h=1)),('top_h_10',dict(top_h=10)),
             ('contact_r_0.005',dict(contact_r=.005)),('airgap_0.2mm',dict(contact_r=.0002/.026)),
             ('airgap_1mm',dict(contact_r=.001/.026)),('deck_k_0.03',dict(deck_k=.03)),
             ('deck_k_0.12',dict(deck_k=.12)),('deck_k_0.20',dict(deck_k=.20)),
             ('food_k_0.3',dict(food_k=.3)),('food_k_0.6',dict(food_k=.6)),
             ('lateral_mixing_10x',dict(lateral_multiplier=10)),
             ('zero_food_vertical_resistance',dict(half_food_resistance=False)),
             ('fill_depth_16mm',dict(depth=.016)),('cold_cap_2C',dict(cold=2)),
             ('ambient_30C_underside_35C',dict(ambient=30,underside=35)),
             ('side_h_5',dict(side_h=5)),('precooled_enclosure_10C',dict(ambient=10,underside=10))]
    cases += [(name,replace(p,**change)) for name,change in changes]
    rows=[]
    for name,params in cases:
        m=Model(params)
        t,it,res=m.solve()
        row=dict(case=name,**m.stats(t),iterations=it,residual_l2_W=res)
        assert abs(row['balance_W']) < 1e-7
        assert min(params.cold,params.ambient,params.underside)-1e-7 <= min(t)
        assert max(t) <= max(params.cold,params.ambient,params.underside)+1e-7
        rows.append(row)
        if name in ('local_baseline','full_plate_reference'):
            write_csv(out/f'{name}_field.csv',[dict(x_mm=x,y_mm=y,temperature_C=v,cold_fraction=f)
                      for (x,y),v,f in zip(m.xy,t,m.fraction)])
            heatmap(out/f'{name}.svg',m,t,name.replace('_',' '))
    write_csv(out/'steady_cases.csv',rows)
    convergence=[]
    for dx in (4,2,1,.5):
        m=Model(replace(p,dx_mm=dx))
        t,it,res=m.solve()
        convergence.append(dict(dx_mm=dx,**m.stats(t),iterations=it,residual_l2_W=res))
    write_csv(out/'grid_convergence.csv',convergence)
    transient=[]
    # Backward Euler, sample every 15 min; include time-step convergence at 2 h.
    time_convergence=[]
    for full in (False,True):
        m=Model(replace(p,full_plate=full))
        for start in (4,25):
            for dt in (60,300):
                t=[float(start)]*m.n
                extra=m.capacity/dt
                for sec in range(0,4*3600+1,dt):
                    if dt==60 and sec%900==0:
                        transient.append(dict(plate='full' if full else 'local',initial_C=start,time_min=sec/60,**m.stats(t)))
                    if sec==7200:
                        time_convergence.append(dict(plate='full' if full else 'local',initial_C=start,dt_s=dt,time_min=120,**m.stats(t)))
                    if sec<4*3600:
                        t,_,_=m.solve(rhs=[b+extra*v for b,v in zip(m.rhs,t)],initial=t,extra=extra)
    write_csv(out/'transient.csv',transient)
    write_csv(out/'time_convergence.csv',time_convergence)
    report=dict(parameters=asdict(p),cases={name:asdict(param) for name,param in cases},checks=checks(),
                steady=rows,grid_convergence=convergence,time_convergence=time_convergence,
                footprints=compare_footprints(out,p),
                conventions={'temperature':'thickness-averaged food, deg C', 'cold_W':'positive heat extracted',
                             'balance_W':'ambient + underside - extraction; equals storage rate in transient'})
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(checks=report['checks'],baseline=rows[0],full_plate=rows[1]),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'output')
    parser.add_argument('--checks-only',action='store_true')
    args=parser.parse_args()
    if args.checks_only:
        print(json.dumps(checks(),indent=2))
    else:
        run(args.output)
