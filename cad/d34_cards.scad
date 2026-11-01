// D34 card models in the plenum bays, from cad/generated/d34_cards_data.scad
// (scripts/gen_d34_cards.py reads the KiCad boards). Included by plenum.scad,
// which defines pl_card_in, pl_card_top and the card frames.
// Board coordinates: u right, v down from the top-left corner seen from the
// component side; w = height above the component face (toward the axis).
// Heights come from the catalogue; mated-plug heights and withdrawal travel are
// estimates. Geometry study only: no part has been fitted.
include <generated/d34_cards_data.scad>

d34_grip = 8;         // finger/plug-grip clearance on the gripped faces (criterion, 2026-10-26 final)
d34_grip_end = 0;     // no clearance needed beyond the faces that are not gripped
d34_grip_pull = 5;    // extra withdrawal beyond the engagement travel

function d34_model(name) = d34_card_models[search([name],d34_card_models,1,0)[0]];
function d34_conn(m,ref) = m[4][search([ref],m[4],1,0)[0]];
function d34_card_angle(name) = pl_cards[search([name],pl_cards,1,0)[0]][1];

// Board coordinates -> card frame (x radial, y tangential, z up). det = -1:
// (u,v,w) is left-handed, so this matrix is a proper map, not a mirror error.
d34_M = [[0,0,-1,pl_card_in],[-1,0,0,pl_card[0]/2],[0,-1,0,pl_card_top],[0,0,0,1]];
function d34_local(u,v,w) = [pl_card_in-w, pl_card[0]/2-u, pl_card_top-v];
function d34_global(name,u,v,w) =
    let(a=d34_card_angle(name), p=d34_local(u,v,w))
    [p[0]*cos(a)-p[1]*sin(a), p[0]*sin(a)+p[1]*cos(a), p[2]];
// Board direction (du,dv,dw) -> assembly direction (left-handed board frame).
function d34_gdir(name,d) = let(a=d34_card_angle(name), l=[-d[2],-d[0],-d[1]])
    [l[0]*cos(a)-l[1]*sin(a), l[0]*sin(a)+l[1]*cos(a), l[2]];
function d34_dir(name) = d34_gdir(name,[0,0,1]);
// Lead exit: the face centre and direction given by parts3d (else the plug top, +w).
function d34_port(name,ref) =
    let(m=d34_model(name), c=d34_conn(m,ref))
    [d34_global(name,c[8][0],c[8][1],c[11]), d34_gdir(name,c[12])];

module d34_in_bay(name) {
    rotate([0,0,d34_card_angle(name)]) multmatrix(d34_M) children();
}
module d34_box(b,w0,w1,grow=[0,0],sweep=0) {
    translate([b[0]-grow[0],b[1]-grow[1]-sweep,w0])
        cube([b[2]-b[0]+2*grow[0],b[3]-b[1]+2*grow[1]+sweep,w1-w0]);
}

module d34_board(m) {
    r = 1;
    translate([0,0,-m[2]]) linear_extrude(m[2])
        offset(r=r) offset(delta=-r) square(m[1]);
}
// Trimmed leads on the solder side, under each body footprint [estimate].
module d34_solder(m) {
    if(len(m[5])>0) for(s=m[5]) d34_box(s[0],s[1],s[2]+0.01);   // parts3d solder tails
    else intersection() {                                         // fallback: every footprint
        for(p=m[3]) d34_box(p[3],-m[2]-pl_card_solder,-m[2]+0.01);
        translate([0,pl_card_band,-10]) cube([m[1][0],m[1][1]-2*pl_card_band,20]);
    }
}
module d34_part(p,sweep=0) {
    b = p[3];
    if(p[2]=="cyl" && sweep==0)
        translate([(b[0]+b[2])/2,(b[1]+b[3])/2,p[4]])
            cylinder(d=min(b[2]-b[0],b[3]-b[1]),h=p[5]-p[4],$fn=24);
    else d34_box(b,p[4],p[5],sweep=sweep);
}
module d34_parts(m,sweep=0) { for(p=m[3]) d34_part(p,sweep); }
module d34_plug(c,sweep=0) { d34_box(c[3],c[4],c[5],sweep=sweep); }
function d34_in(ref,list) = len([for(x=list) if(x==ref) 1]) > 0;
// A connector no harness lead uses (e.g. the spare tec J7) has no mated plug.
function d34_used(card,ref) = is_undef(harness_used_ports) || d34_in(str(card,":",ref),harness_used_ports);

// Finger/plug-grip volume: the exposed plug housing grown on its pinch faces,
// swept outward by the engagement travel plus a pull allowance.
// mode "pinch": fingers on the two faces across the narrow plan dimension;
// mode "ends": fingers on the two faces across the long dimension.
function pl_grip_mode(card,ref) =
    let(o=[for(x=is_undef(pl_grip_modes) ? [] : pl_grip_modes) if(x[0]==card && x[1]==ref) x[2]])
    len(o)>0 ? o[0] : "pinch";
module d34_grip(c,mode="pinch") {
    ax = mode=="pinch" ? c[7] : (c[7]=="v" ? "u" : "v");
    g = ax=="v" ? [d34_grip_end,d34_grip] : [d34_grip,d34_grip_end];
    hull() {
        d34_box(c[3],c[4],c[5],grow=g);
        d34_box(c[3],c[4]+c[6]+d34_grip_pull,c[5]+c[6]+d34_grip_pull,grow=g);
    }
}

// ---------- Assembly-frame modules, one or all cards.
module pl_d34_boards() {
    for(c=pl_cards) let(m=d34_model(c[0])) d34_in_bay(c[0]) { d34_board(m); d34_solder(m); }
}
module pl_d34_bodies(sweep=false) {
    // Sweep: lifted straight up (−v) from the seat to above the lid.
    for(c=pl_cards) let(m=d34_model(c[0])) d34_in_bay(c[0])
        d34_parts(m,sweep ? lid_z+10-pl_floor_z : 0);
}
module pl_d34_plugs(card=undef,except=[]) {
    for(c=pl_cards) if(is_undef(card) || c[0]==card) let(m=d34_model(c[0]))
        d34_in_bay(c[0]) for(k=m[4]) if(!d34_in(k[0],except) && d34_used(c[0],k[0])) d34_plug(k);
}
module pl_d34_cards(sweep=false) {
    // Board, solder side and component bodies (unmated). Sweep for top loading.
    for(c=pl_cards) let(m=d34_model(c[0])) d34_in_bay(c[0]) {
        s = sweep ? lid_z+10-pl_floor_z : 0;
        translate([0,-s,0]) d34_board(m);
        if(sweep) d34_box([0,0,m[1][0],m[1][1]],-m[2],0,sweep=s);
        d34_solder(m);
        if(sweep) d34_box([0,pl_card_band,m[1][0],m[1][1]-pl_card_band],
                          -m[2]-pl_card_solder,-m[2],sweep=s);
        d34_parts(m,s);
    }
}
module pl_d34_installed() { pl_d34_cards(); pl_d34_plugs(); }
module pl_d34_grip(card,ref) {
    m = d34_model(card);
    d34_in_bay(card) d34_grip(d34_conn(m,ref));
}
module pl_d34_colour() {
    for(c=pl_cards) let(m=d34_model(c[0])) d34_in_bay(c[0]) {
        color("DarkGreen") d34_board(m);
        for(p=m[3]) color(p[6]) d34_part(p);
        for(k=m[4]) if(d34_used(c[0],k[0])) color("Ivory") d34_plug(k);
    }
}

// ---------- Hand access (order and card-internal crowding: scripts/access_order.py).
module d34_access(c,mode="pinch") {  // grip volume plus a vertical approach from above (−v)
    hull() { d34_grip(c,mode); translate([0,-120,0]) d34_grip(c,mode); }
}
module pl_d34_access(card,ref,mode=undef) {
    m = d34_model(card);
    if(d34_used(card,ref))
    d34_in_bay(card) d34_access(d34_conn(m,ref),is_undef(mode) ? pl_grip_mode(card,ref) : mode);
}
module pl_d34_plugs_mated(card,removed=[]) {
    for(c=pl_cards) let(m=d34_model(c[0])) d34_in_bay(c[0])
        for(k=m[4]) if((c[0]!=card || !d34_in(k[0],removed)) && d34_used(c[0],k[0])) d34_plug(k);
}
