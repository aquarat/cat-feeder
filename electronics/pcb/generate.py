#!/usr/bin/env python3
"""Generate editable KiCad 9 circuit/placement from explicit connectivity.

Run with /usr/bin/python3 in the supplied Docker image. The routed board is
produced separately by route.py: regenerating never silently reuses old copper.
"""
import collections, copy, csv, json, math, pathlib, re, shutil, uuid
import pcbnew as p
import outline
import project_rules

ROOT=pathlib.Path(__file__).resolve().parent
NS=uuid.UUID('62907cff-bc53-48c1-a346-62d027c321ed')
def uid(s): return str(uuid.uuid5(NS,s))
SHEET=uid('sheet')
def q(s): return json.dumps(str(s))
def xy(x,y): return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def mm(v): return p.ToMM(v)

# Small S-expression parser retains quoted strings for exact library copying.
def parse(s):
    toks=re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+',s)
    stack=[];root=None
    for t in toks:
        if t=='(':
            a=[]
            if stack:stack[-1].append(a)
            else:root=a
            stack.append(a)
        elif t==')':stack.pop()
        else:stack[-1].append(t)
    return root
def dump(a): return '('+' '.join(dump(x) if isinstance(x,list) else x for x in a)+')'
def kids(a,k):return [x for x in a if isinstance(x,list) and x and x[0]==k]
def kid(a,k):return next(iter(kids(a,k)),None)
def unq(s):return json.loads(s) if s.startswith('"') else s
LIBCACHE={}
def libsymbol(libid):
    lib,name=libid.split(':')
    if lib not in LIBCACHE:
        LIBCACHE[lib]={unq(s[1]):s for s in kids(parse(pathlib.Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text()),'symbol')}
    def resolve(n):
        s=copy.deepcopy(LIBCACHE[lib][n]);ext=kid(s,'extends')
        if ext:
            base=resolve(unq(ext[1]));base[1]=q(n)
            for sub in kids(base,'symbol'):sub[1]=q(unq(sub[1]).replace(unq(ext[1])+'_',n+'_',1))
            keys={unq(x[1]) for x in kids(s,'property')}
            base=[x for x in base if not(isinstance(x,list) and x[0]=='property' and unq(x[1]) in keys)]
            base.extend(kids(s,'property'));s=base
        return s
    s=resolve(name);s[1]=q(libid);return s

PARTS=[]
def add(ref,value,lib,fp,nets,pos,lcsc='',assembly='SMT',pins=None):
    PARTS.append(dict(ref=ref,value=value,lib=lib,fp=fp,nets={str(k):v for k,v in nets.items()},
                      pos=pos,lcsc=lcsc,assembly=assembly,uuid=uid(ref),pins=pins))

RFP='Resistor_SMD:R_0603_1608Metric'
CFP='Capacitor_SMD:C_0603_1608Metric'
SOT='Package_TO_SOT_SMD:SOT-23-5'
HDR='Connector_PinHeader_2.54mm:PinHeader_1x{:02d}_P2.54mm_Vertical'
SOCK='Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical'
TERM='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'

# Espressif module pin numbers, not bare-chip pad numbers.
add('U1','ESP32-WROOM-32E-N4','RF_Module:ESP32-WROOM-32E','RF_Module:ESP32-WROOM-32E',{
 1:'GND',2:'+3V3',3:'EN',6:'FAN_TACH',7:'BUS_SENSE',8:'INDEX',9:'HOME',
 10:'TEC_EN',11:'FAN_PWM_GPIO',12:'ONEWIRE',15:'GND',16:'UART_OEn',
 25:'BOOT',27:'DPS_RX',28:'DPS_TX',30:'STEP',31:'DIR',33:'I2C_SDA',
 34:'U0RX',35:'U0TX',36:'I2C_SCL',37:'MOTOR_RUN',38:'GND',39:'GND'},
 (75,63,0),'C701341')
add('U2','AP2112K-3.3TRG1','Regulator_Linear:AP2112K-3.3',SOT,
 {1:'+5V',2:'GND',3:'+5V',5:'+3V3'},(59,65,0),'C51118')
# Two separately available single gates avoid a finer-pitch dual footprint.
add('U3','SN74LVC1G125DBVR','74xGxx:74LVC1G125',SOT,
 {1:'UART_OEn',2:'DPS_TX',3:'GND',4:'DPS_TX_BUF',5:'+3V3'},(82,104,0),'C23654')
add('U4','SN74LVC1G125DBVR','74xGxx:74LVC1G125',SOT,
 {1:'UART_OEn',2:'DPS_TX_EXT',3:'GND',4:'DPS_RX',5:'+3V3'},(87,104,0),'C23654')
add('Q1','MMBT3904','Transistor_BJT:MMBT3904','Package_TO_SOT_SMD:SOT-23',
 {1:'FAN_BASE',2:'GND',3:'FAN_PWM_OD'},(87,79,0),'C20526')

def resistor(n,value,a,b,x,y,rot=0):
    code={'10k':'C25804','100k':'C25803','4.7k':'C23162','1k':'C21190'}[value]
    add('R'+str(n),value,'Device:R',RFP,{1:a,2:b},(x,y,rot),code)
resistor(1,'10k','+3V3','EN',60,73)
resistor(2,'10k','+3V3','BOOT',81,86)
resistor(3,'4.7k','+3V3','ONEWIRE',58,79)
resistor(4,'10k','+3V3','INDEX',59,83)
resistor(5,'10k','+3V3','HOME',63,83)
resistor(6,'10k','+3V3','TACH_EXT',88,73)
resistor(7,'1k','TACH_EXT','FAN_TACH',88,69)
resistor(8,'4.7k','FAN_PWM_GPIO','FAN_BASE',87,83)
resistor(9,'100k','FAN_BASE','GND',82,83)
resistor(10,'10k','TEC_EN','GND',88,110)
resistor(11,'10k','MOTOR_RUN','GND',69,83)
resistor(12,'100k','STEP','GND',73,83)
resistor(13,'100k','DIR','GND',77,83)
resistor(14,'10k','+3V3','UART_OEn',82,110)
resistor(15,'1k','DPS_TX_BUF','DPS_RX_EXT',86,115)
resistor(16,'4.7k','+3V3','I2C_SDA',88,63)
resistor(17,'4.7k','+3V3','I2C_SCL',88,59)
resistor(18,'100k','VMOT','BUS_SENSE',77,97,90)
resistor(19,'10k','BUS_SENSE','GND',77,101,90)
# Review B1: OE bias does not prevent floating CMOS data inputs.
resistor(20,'10k','+3V3','DPS_TX',79,113)
resistor(21,'10k','DPS_TX_EXT','GND',91,109,90)

def cap(n,value,a,b,x,y,rot=0):
    code={'100n':'C14663','10u 25V':'C15850','1u 50V':'C15849'}[value]
    fp='Capacitor_SMD:C_0805_2012Metric' if value=='10u 25V' else CFP
    add('C'+str(n),value,'Device:C',fp,{1:a,2:b},(x,y,rot),code)
cap(1,'10u 25V','+5V','GND',59,60)
cap(2,'10u 25V','+3V3','GND',59,69)
cap(3,'100n','+3V3','GND',63,66,90)
cap(4,'10u 25V','+3V3','GND',63,61,90)
cap(5,'1u 50V','EN','GND',63,73)
cap(6,'100n','+3V3','GND',82,100)
cap(7,'100n','+3V3','GND',87,100)
cap(8,'100n','BUS_SENSE','GND',77,105,90)
cap(9,'100n','+3V3','GND',78,89)
add('C10','100u 50V EEUFR1H101B','Device:C_Polarized',
 'Capacitor_THT:CP_Radial_D8.0mm_P5.00mm',{1:'VMOT',2:'GND'},(82,94,0),'C713402','THT')
cap(11,'10u 25V','+12V','GND',93,84)

def header(ref,value,n,nets,x,y,rot=0,fp=None,lcsc=''):
    if not lcsc:lcsc={2:'C27985187',3:'C49257',4:'C5116483',8:'C27438'}[n]
    add(ref,value,f'Connector_Generic:Conn_01x{n:02d}',fp or HDR.format(n),
        dict(enumerate(nets,1)),(x,y,rot),lcsc,'THT')
header('J1','VMOT 20-24V INPUT',2,['VMOT','GND'],85.5,123,0,TERM,'C5183929')
header('J2','RAILS GND-5V-12V',3,['GND','+5V','+12V'],94,88)
header('J3','FAN GND-12V-TACH-PWM',4,['GND','+12V','TACH_EXT','FAN_PWM_OD'],94,73)
header('J4','DS18B20 GND-DQ-3V3',3,['GND','ONEWIRE','+3V3'],54,76)
header('J5','DS18B20 GND-DQ-3V3',3,['GND','ONEWIRE','+3V3'],54,85)
header('J6','INDEX GND-SIG-3V3',3,['GND','INDEX','+3V3'],54,96)
header('J7','HOME GND-SIG-3V3',3,['GND','HOME','+3V3'],54,105)
header('J8','I2C GND-3V3-SDA-SCL',4,['GND','+3V3','I2C_SDA','I2C_SCL'],94,59)
header('J9','DPS GND-RX-TX (DPS names)',3,['GND','DPS_RX_EXT','DPS_TX_EXT'],94,101)
header('J10','TEC ENABLE GND-ON',2,['GND','TEC_EN'],94,112)
header('J11','PROG GND-TX-RX-3V3ref',4,['GND','U0TX','U0RX','+3V3'],54,60)
header('J12','BOOT short for download',2,['BOOT','GND'],78,78.5,90)
header('J13','RESET short to reset',2,['EN','GND'],54,72.2,90)
# Two rows 15.24 mm apart, standard Pololu carrier viewed from component side.
# Left top->bottom EN,MS1,MS2,MS3,RST,SLP,STEP,DIR.
# Right top->bottom VMOT,GND,2B,2A,1A,1B,VDD,GND.
header('J14','A4988 CONTROL socket',8,['GND','+3V3','+3V3','+3V3',
 'MOTOR_RUN','MOTOR_RUN','STEP','DIR'],59,91,0,SOCK)
header('J15','A4988 POWER socket',8,['VMOT','GND','M2B','M2A','M1A','M1B','+3V3','GND'],74.24,91,0,SOCK)
header('J16','MOTOR COIL1',2,['M1A','M1B'],58,123,0,TERM,'C5183929')
header('J17','MOTOR COIL2',2,['M2A','M2B'],70,123,0,TERM,'C5183929')

def make_schematic():
    libs={a['lib']:libsymbol(a['lib']) for a in PARTS}
    libs['power:PWR_FLAG']=libsymbol('power:PWR_FLAG')
    head=f'''(kicad_sch (version 20250114) (generator "eeschema")
      (uuid "{SHEET}") (paper "A2")
      (title_block (title "Cat feeder controller / module carrier - DRAFT A")
       (date "2026-10-24") (rev "A-draft")
       (comment 1 "External protected 20/24V motor, 5V logic and 12V fan rails. TEC power external.")
       (comment 2 "3.3V GPIO; DPS UART qualification required. A4988 and harnesses separately fitted."))
      (lib_symbols {' '.join(dump(s) for s in libs.values())})'''
    out=[head]
    # Four functional rows: MCU/power, interface logic, resistors, connectors.
    locations={'U1':(65,80),'U2':(160,45),'U3':(250,45),'U4':(340,45),'Q1':(430,45)}
    groups=[([a for a in PARTS if a['ref'].startswith('R')],140,5,80),
            ([a for a in PARTS if a['ref'].startswith('C')],250,6,75),
            ([a for a in PARTS if a['ref'].startswith('J')],330,9,62)]
    for seq,start,cols,step in groups:
        for i,a in enumerate(seq):locations[a['ref']]=(40+(i%cols)*step,start+(i//cols)*25)
    locations['R21']=(440,215)  # Keep its labels clear of the capacitor row.
    for a in PARTS:
        x,y=[round(round(v/1.27)*1.27,4) for v in locations[a['ref']]];s=libs[a['lib']];pins=[]
        for sub in kids(s,'symbol'):
            for pin in kids(sub,'pin'):
                pins.append(pin)
        props=[f'(property "Reference" {q(a["ref"])} (at {x} {y-10} 0) (effects (font (size 1.27 1.27))))',
               f'(property "Value" {q(a["value"])} (at {x} {y-7.5} 0) (effects (font (size 1 1))))',
               f'(property "Footprint" {q("feeder:"+a["fp"].split(":")[1])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))',
               f'(property "LCSC" {q(a["lcsc"])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))']
        # Keep text clear of labelled vertical pins; ERC does not check typography.
        top=min(y-float(kid(pin,'at')[2]) for pin in pins)
        rx,ry,vx,vy=x,top-6.35,x,top-3.81
        if a['ref'][0] in 'RC':rx,ry,vx,vy=x+12,y-1.27,x+12,y+1.27
        props[0]=f'(property "Reference" {q(a["ref"])} (at {rx} {ry} 0) (effects (font (size 1.27 1.27))))'
        props[1]=f'(property "Value" {q(a["value"])} (at {vx} {vy} 0) (effects (font (size 1 1))))'
        instance=f'''(symbol (lib_id {q(a['lib'])}) (at {x} {y} 0) (unit 1)
          (in_bom yes) (on_board yes) (dnp no) (uuid "{a['uuid']}")
          {' '.join(props)}
          (instances (project "feeder" (path "/{SHEET}" (reference {q(a['ref'])}) (unit 1)))))'''
        out.append(instance)
        for pin in pins:
            number=unq(kid(pin,'number')[1]);at=kid(pin,'at');px=x+float(at[1]);py=y-float(at[2]);angle=float(at[3])
            net=a['nets'].get(number)
            if net is None:
                out.append(f'(no_connect (at {px} {py}) (uuid "{uid(a["ref"]+number+"NC")}"))')
                continue
            # Outward 2.54mm wire; pin angle points inward to symbol body.
            ex=round(px-2.54*math.cos(math.radians(angle)),4)
            ey=round(py+2.54*math.sin(math.radians(angle)),4)
            out.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(a["ref"]+number+"wire")}"))')
            la=0 if angle in (0,90,270) else 180
            out.append(f'(label {q(net)} (at {ex} {ey} {la}) (effects (font (size 0.9 0.9)) (justify left bottom)) (uuid "{uid(a["ref"]+number+"label")}"))')
    for i,net in enumerate(['GND','+5V','+12V','VMOT']):
        x,y=round(round((155+i*40)/1.27)*1.27,4),95.25;ref='#FLG0'+str(i+1)
        out.append(f'''(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1)
          (in_bom no) (on_board yes) (dnp no) (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
          (property "Value" "PWR_FLAG" (at {x} {y-4} 0) (effects (font (size 1 1))))
          (instances (project "feeder" (path "/{SHEET}" (reference "{ref}") (unit 1)))))
          (label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid "{uid(ref+'label')}"))''')
    out.append(')');(ROOT/'feeder.kicad_sch').write_text('\n'.join(out))
    # Local library table makes the native library symbols discoverable in GUI/ERC.
    table='(sym_lib_table (version 7)\n'+''.join(f'(lib (name "{lib}") (type "KiCad") (uri "${{KICAD9_SYMBOL_DIR}}/{lib}.kicad_sym") (options "") (descr ""))\n' for lib in sorted({k.split(':')[0] for k in libs}))+')\n'
    (ROOT/'sym-lib-table').write_text(table)

def make_board():
    b=p.BOARD();b.SetCopperLayerCount(2)
    ds=b.GetDesignSettings();ds.m_MinClearance=p.FromMM(.2);ds.m_CopperEdgeClearance=p.FromMM(.3)
    nc=ds.m_NetSettings.GetDefaultNetclass();nc.SetClearance(p.FromMM(.2));nc.SetTrackWidth(p.FromMM(.25));nc.SetViaDiameter(p.FromMM(.6));nc.SetViaDrill(p.FromMM(.3))
    nets={}
    for name in sorted({n for a in PARTS for n in a['nets'].values()}):
        nets[name]=p.NETINFO_ITEM(b,name);b.Add(nets[name])
    fpdir=ROOT/'feeder.pretty';fpdir.mkdir(exist_ok=True)
    for a in PARTS:
        lib,name=a['fp'].split(':');f=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name)
        assert f,a['fp'];f.SetReference(a['ref']);f.SetValue(a['value']);f.SetPosition(xy(*a['pos'][:2]));f.SetOrientationDegrees(a['pos'][2])
        f.SetPath(p.KIID_PATH('/'+SHEET+'/'+a['uuid']))
        f.Value().SetVisible(False);f.Reference().SetTextSize(xy(.8,.8));f.Reference().SetTextThickness(p.FromMM(.12))
        # Reference marks sit beside tight edge headers, not over the adjacent one.
        if a['ref'] in ['J4','J5','J6','J7']:
            f.Reference().SetPosition(xy(51.5,a['pos'][1]+2.54));f.Reference().SetTextAngle(p.EDA_ANGLE(90,p.DEGREES_T))
        if a['ref'] in ['R18','R19','C8']:
            f.Reference().SetPosition(xy(79,a['pos'][1]));f.Reference().SetTextAngle(p.EDA_ANGLE(90,p.DEGREES_T))
        if a['ref']=='C11':f.Reference().SetPosition(xy(96,84))
        if a['ref']=='R21':f.Reference().SetPosition(xy(89.8,109));f.Reference().SetTextAngle(p.EDA_ANGLE(90,p.DEGREES_T))
        # Local copied footprint library keeps exact geometry editable/portable.
        f.SetFPID(p.LIB_ID('feeder',name))
        for pad in f.Pads():
            n=a['nets'].get(pad.GetNumber())
            if n:pad.SetNet(nets[n])
        b.Add(f)
        # Sockets' courtyard only encloses connector body, not the added module.
        local=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name)
        # KiCad trims placed keepouts to enabled layers. Match this two-layer
        # board in the local library, retaining front AND back antenna exclusion.
        for zone in local.Zones():
            layers=p.LSET();layers.AddLayer(p.F_Cu);layers.AddLayer(p.B_Cu);zone.SetLayerSet(layers)
        p.PCB_IO_KICAD_SEXPR().FootprintSave(str(fpdir),local)
    # Compact crescent wall segment. The long curved edges follow R91/R141;
    # four 2mm corner fillets, zero mounting holes. No enclosure fit assertion.
    for start,end in outline.LINES:
        s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(xy(*start));s.SetEnd(xy(*end));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));b.Add(s)
    for start,mid,end in outline.ARCS:
        s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_ARC);s.SetArcGeometry(xy(*start),xy(*mid),xy(*end));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));b.Add(s)
    # Explicit all-layer antenna exclusion. Library footprint additionally has its own keepout.
    z=p.ZONE(b);z.SetIsRuleArea(True);layers=p.LSET();layers.AddLayer(p.F_Cu);layers.AddLayer(p.B_Cu);z.SetLayerSet(layers)
    z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowPads(True);z.SetDoNotAllowFootprints(False);z.SetZoneName('ESP32 antenna - no copper on any layer')
    z.Outline().NewOutline()
    for x,y in [(40,50),(100,50),(100,56.7),(40,56.7)]:z.Outline().Append(p.FromMM(x),p.FromMM(y))
    b.Add(z)
    # Fabrication module envelope documents carrier height/area without adding fake PCB pads.
    s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_RECT);s.SetStart(xy(57,88.5));s.SetEnd(xy(76.3,111));s.SetLayer(p.Dwgs_User);s.SetWidth(p.FromMM(.15));b.Add(s)
    for text,x,y,size in [('CAT FEEDER A / DRAFT',75,129,1),('ANTENNA / KEEP CLEAR',75,52,1),('A4988 / VMOT ->',66.5,88,.8),('NO TEC POWER ON PCB',69,115,.8)]:
        t=p.PCB_TEXT(b);t.SetText(text);t.SetPosition(xy(x,y));t.SetTextSize(xy(size,size));t.SetTextThickness(p.FromMM(.12));t.SetLayer(p.F_SilkS);b.Add(t)
    b.SetFileName(str(ROOT/'feeder-unrouted.kicad_pcb'))
    project_rules.save_board(ROOT/'feeder-unrouted.kicad_pcb',b)
    p.ExportSpecctraDSN(b,str(ROOT/'feeder.dsn'))
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "feeder") (type "KiCad") (uri "${KIPRJMOD}/feeder.pretty") (options "") (descr "Copied KiCad 9.0.2 footprints")))\n')
    # Project rules retained by the editor and DRC, including motor trace classes.
    cls=lambda name,w:dict(name=name,clearance=.2,track_width=w,via_diameter=.6,via_drill=.3,
                          diff_pair_width=.2,diff_pair_gap=.25,diff_pair_via_gap=.25,
                          microvia_diameter=.3,microvia_drill=.1,wire_width=6,bus_width=12)
    project={'meta':{'filename':'feeder.kicad_pro','version':1},
      'board':{'design_settings':{'rules':{'min_clearance':.2,'min_track_width':.2,'min_via_diameter':.6,
         'min_through_hole_diameter':.2,'min_copper_edge_clearance':.3,'min_hole_clearance':.25},'rule_severities':{}}},
      'net_settings':{'classes':[cls('Default',.25),cls('Motor',1.0),cls('Power',.5)],
          'netclass_patterns':[{'pattern':prefix+n,'netclass':'Motor'} for prefix in ['', '/'] for n in ['VMOT','M1A','M1B','M2A','M2B']]+
              [{'pattern':prefix+n,'netclass':'Power'} for prefix in ['', '/'] for n in ['GND','+3V3','+5V','+12V']]}}
    for name in ['feeder','feeder-unrouted']:(ROOT/(name+'.kicad_pro')).write_text(json.dumps(project,indent=2)+'\n')
    for name in ['feeder','feeder-unrouted']:project_rules.validate(ROOT/(name+'.kicad_pro'))
    # DSN width rules; pcbnew exporter uses default until project reopened.
    dsn=(ROOT/'feeder.dsn').read_text();i=dsn.rfind('\n  (wiring')
    # Class declarations are inside network; insert before its closing paren.
    marker='\n  (wiring';end=dsn.index(marker);network_end=dsn.rfind(')',0,end)
    classes='\n    (class motor VMOT M1A M1B M2A M2B (circuit (use_via "Via[0-1]_600:300_um")) (rule (width 1000) (clearance 200)))\n'
    # Exported via padstack ID is discovered rather than guessed.
    via=re.search(r'\(via\s+([^\s)]+)',dsn).group(1)
    classes=classes.replace('"Via[0-1]_600:300_um"',via)
    classes+='    (class power GND +3V3 +5V +12V (rule (width 500) (clearance 200)))\n'
    dsn=dsn[:network_end]+classes+dsn[network_end:];(ROOT/'feeder.dsn').write_text(dsn)
    return b

def bom():
    with (ROOT/'design-bom.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','LCSC','Assembly','X_mm','Y_mm','Rotation_deg'])
        for a in PARTS:w.writerow([a['ref'],a['value'],a['fp'],a['lcsc'],a['assembly'],*a['pos']])
    (ROOT/'connectivity.json').write_text(json.dumps(PARTS,indent=2)+'\n')

if __name__=='__main__':
    make_schematic();make_board();bom();print(f'Generated {len(PARTS)} components')
