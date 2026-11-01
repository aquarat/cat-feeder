// 2026-10-10 screwless revision of the 2026-10-06 wide-clip case. Units: mm.
// Provenance and fit/validation limits: README.md. No headers, no switch, no screws.
// Previous screwed source: revisions/2026-10-06-wide-clip.scad.
part = "exploded";
role = "SENSOR";            // "OARS", "SEAT", "ROWER"; label only, not axis mapping
use <dfm.scad>
use <edges.scad>
$fn = 64;
eps = 0.02;

// USER-CONFIRMED cell envelope; measure protection PCB, seams and leads separately.
battery_l = 35;
battery_w = 30;
battery_t = 5;
battery_protection_extra = 2; // PROVISIONAL extra -Y end length beyond confirmed body
battery_xy_clear = 0.6;      // per side, not a swelling specification
battery_growth = 1.0;        // free height above cell, never preload the pouch
battery_tape = 0.5;
connector_w = 8;             // PROVISIONAL mated PicoBlade + heatshrink envelope
connector_l = 12;
connector_h = 5;
pcb_t = 1.6;                 // official KiCad metadata; verify physical board
pcb_clear = 0.25;
pcb_w = 17.8;
pcb_l = 21;
component_h = 3.2;           // provisional height above PCB, includes USB
strap_w = 38;               // user's selected nominal 3.8 cm webbing
strap_clear = 2;
strap_slot_t = 5;           // provisional clearance for stitched hook/loop end
shell_pilot = 3.4;           // legacy seal coupon only; no bolts in this lid
led_skin = 1.0;              // continuous PETG, five 0.2-mm layers

// Separate broad V-saddle. Diameter is preview/check data, NOT a fitted bore.
shaft_d = 40;
saddle_angle = 120;
saddle_liner = 1.0;          // normal thickness of firm rubber on EACH V face
case_grip_t = 0.3;           // thin high-friction film, not compliant mounting foam
saddle_w = 62;
saddle_l = 50;
saddle_contact_w = 36;       // flat case-contact face on print bed
saddle_web = 4;
saddle_edge_r = 1;
saddle_slot_x = 25;
saddle_slope = 1/tan(saddle_angle/2);
saddle_high = saddle_web+saddle_w/2*saddle_slope;

floor_t = 2.4;
// Raised from 10: the base wall must stand above the tray's snap tabs. The
// hinge follows the seam; the clip pin/catch stay at their coupon-proven Z.
seam_z = 14;
roof_t = 2.4;
inside_w = max(40, battery_w + 10);
inside_l = max(44, battery_l + battery_protection_extra + 7);
inside_r = 3.5;
rim_w = 6.5;
outside_w = inside_w + 2*rim_w;
outside_l = inside_l + 2*rim_w;
outside_r = inside_r + rim_w;
// Screwless tray. Its body floats on four flat-printed spring arms whose tips
// rest on base pedestals; snap tabs at the tips sit in wall pockets. Closing
// the lid pushes the board, and with it the tray body, down tray_preload.
// Z values below are the FREE (lid open) state.
tray_travel = 1.0;           // spring travel reserved; hard stop at this drop
tray_preload = 0.6;          // nominal closed drop; +-0.3 tolerance stays in 0..travel
// Body bottom at FULL travel still clears the pack + growth by 0.5 mm.
tray_z = floor_t+battery_tape+battery_t+battery_growth+0.5+tray_travel;
tray_t = 2.4;
tray_top = tray_z+tray_t;
pcb_under = tray_top+max(3.2,4.8-pcb_t);
pcb_top = pcb_under+pcb_t;
pcb_top_closed = pcb_top-tray_preload;   // lid pads touch the board here
lid_top = pcb_top_closed+component_h+roof_t+0.6;
lid_h = lid_top-seam_z;
tray_body_x = battery_w/2+battery_xy_clear+0.3;  // body covers the pack envelope
tray_body_y = inside_l/2-0.3;
arm_slot = 0.7;              // > tab_reach: inward snap deflection room
arm_w = 2.5;                 // in-plane (X): snap stiffness
arm_t = 1.6;                 // vertical (Z): hold-down spring; bottom layers, on the bed
arm_x0 = tray_body_x+arm_slot;
arm_x1 = arm_x0+arm_w;
arm_root = 2;                // half-length of the rigid root block at Y=0
tab_y = 15.25;               // tab / pedestal centre, both ends
tab_l = 3.5;
tab_reach = 0.5;             // tab tip beyond the cavity wall
tab_lead = 1.0;              // lower lead-in height (31 deg from vertical)
groove_d = 0.75;             // pocket depth into the wall: 0.25 behind the tab tip
groove_ceil = tray_z+arm_t;  // 45-degree retaining ceiling starts here at the pocket back
arm_l = tab_y-arm_root;      // cantilever length to the tab/pedestal centre
pad_u = [7.7,8.8];           // lid pad on the bare edge land (old clamp toe was 7.4..8.9)
pad_v = 4;                   // pad length along the board edge
board_x = 0;
board_y = 9.5;
battery_x = 0;
battery_y = -1.5;           // protection/lead reserve is now at the -Y end
conn_x = 11;
conn_y = -8.5;
gland_offset = 2.8;
gland_w = 2.4;
gland_d = 1.5;              // 2 mm silicone cord: 25% nominal squeeze
cord_d = 2;
clamp_y = -1;               // board-local Y of the edge seats and lid pads
strap_y = 0;
ear_slot_x = outside_w/2+5.5;
ear_outer_x = outside_w/2+11;
pin_d = 1.75;              // purchased PETG filament; heat-headed after insertion
pin_bore = 2.2;            // horizontal slot width; NOT the vertical closure clearance
pin_fit_h = 1.8;           // matched to 1.75-mm filament, flat short bridged roofs
$pin_fit_h = pin_fit_h;    // dynamic override only for manufacturing-limit checks
$lid_part = "all";         // "shell" / "pads": sweeps check the pads against the closed board
pin_play_limit = 0.10;     // maximum MEASURED relative upward movement of two journals
hinge_y = outside_l/2+3.5;
hinge_z = seam_z+0.1;      // 1.8-mm hole faces fall on 0.2-mm print layer boundaries
open_angle = 120;
latch_pin_z = 12.1;        // hole floor 11.2 and roof 13.0, both 0.2-mm layer boundaries
clip_preload = 0.2;        // free hook is 0.2 below the closed catch bearing plane
clip_release = 0.40;       // wider bearing needs 0.20 mm lift beyond closed position
clip_park = 62;            // longer spring parks above straps, positive stop
catch_z = 16;
clip_w = 16;              // doubled bearing width after fragile first-coupon feedback
clip_t = 1.4;             // longer spring allows a thicker section at lower strain
clip_arm_u = 6.7;
clip_beam_start = 1.4;      // compliant span begins beyond the wider catch bearing
clip_hook_t = 2.0;         // reinforced toe, independent of compliant beam thickness
clip_hook_l = 1.3;
clip_tab_u = 8.2;
clip_mount_w = clip_w+7;   // two 3.1-mm journals and two 0.4-mm running gaps
catch_tip_u = 1.3;         // 1.0-mm bearing depth (previously 0.7)
hook_u = 0.3;             // bearing is OUTBOARD of pin: gasket reaction seats latch inward
clip_stop_z = -2.5*sin(clip_park)-cos(clip_park);
clip_stop_u = 2.5*cos(clip_park)-sin(clip_park)-0.65;
round_pin_slop = (pin_bore-pin_d)/2;

assert(battery_l>0 && battery_w>0 && battery_t>0);
assert(battery_protection_extra>=0);
assert(pcb_t>=0.6 && pcb_t<=2);
assert(lid_top-roof_t >= pcb_top_closed+component_h+0.59, "Component headroom, lid closed");
assert(led_skin>=0.8 && led_skin<=roof_t);
assert(gland_offset-gland_w/2>=1.4, "Inner sealing land");
assert(rim_w-gland_offset-gland_w/2>=1.4, "Outer sealing land");
assert(PI*cord_d*cord_d/4/(gland_w*gland_d)<0.9, "Gland fill");
assert(board_y+8.6056 > battery_y+battery_l/2+2,
       "Entire antenna body must project beyond cell metal by >=2 mm");
assert(tray_z-tray_travel >= floor_t+battery_tape+battery_t+battery_growth+0.49,
       "Tray at full spring travel must still clear pack + growth by 0.5 mm");
assert(tray_preload>=0.45 && tray_preload<=tray_travel-0.35,
       "Nominal preload needs >=0.3 mm tolerance band both ways");
assert(arm_x1 <= inside_w/2-0.5, "Arm running clearance to the wall");
assert(tab_reach < arm_slot-0.1, "Snap deflection must not close the arm slot");
assert(groove_d-tab_reach >= 0.2, "Pocket back clearance behind the tab tip");
assert(tab_y+tab_l/2+0.3 <= inside_l/2-inside_r, "Tab pockets stay on the straight wall");
assert(groove_ceil+groove_d <= seam_z-1.2,
       "Intact wall above each pocket: sealing lands are not notched");
assert(gland_offset-gland_w/2-groove_d >= 0.8, "Wall between tab pocket and gland");
assert(pcb_top+1.6-3.5 >= seam_z+1.5, "USB cable body clears the raised base rim");
assert(abs(seam_z/0.2-round(seam_z/0.2))<1e-6 && abs(lid_top/0.2-round(lid_top/0.2))<1e-6,
       "Seam and lid top on 0.2 mm layers keep the hinge journals on layer boundaries");
assert(catch_z-1.2 > seam_z+0.5, "Clip catch root stays on the lid wall above the seam");
assert(3*arm_t*tray_travel/(2*arm_l*arm_l) < 0.015, "Spring-arm strain at full travel");
assert(connector_w<=8 && connector_l<=13 && connector_h<=7,
       "Connector exceeds reserved bay: relayout before export");
assert(strap_slot_t>=2.5 && strap_slot_t<=6, "Keep at least 2.5 mm on ear outer bar");
assert(battery_xy_clear>=0.3 && battery_xy_clear<=0.8);
assert(saddle_angle>=110 && saddle_angle<=130);
assert(saddle_liner>=0.5 && saddle_liner<=1.5);
assert(case_grip_t>=0 && case_grip_t<=0.5);
assert(shaft_d>=25 && shaft_d<=60, "Provisional saddle diameter range is 25–60 mm");
// At the top of a 120-degree V, contact is at x=(R+t)*cos(60), NOT x=R+t.
// Actual curved shaft and strap-route interference is checked below.
assert(saddle_slot_x-strap_slot_t/2-0.8 > (60/2+1.5)*cos(saddle_angle/2)+4,
       "Keep strap guides away from the widest contact band");
assert(saddle_l-(strap_w+strap_clear)>=8, "Saddle strap-slot end lands");
assert(pin_d<pin_bore && pin_bore>=2.05 && pin_bore<=2.35);
assert(clip_preload>=0.1 && clip_preload<=0.3);
assert(hook_u>0 && hook_u<1 && clip_beam_start>1,
       "Hook bearing must remain outboard of pivot to seat under gasket load");
assert(pin_fit_h>pin_d && pin_fit_h-pin_d<=pin_play_limit);
assert(clip_preload-pin_play_limit>=0.099,
       "Default closure needs >=0.10 mm residual spring lift after measured journal play");

module rr(w,l,r) { offset(r=r) square([w-2*r,l-2*r],center=true); }
module outline() { rr(outside_w,outside_l,outside_r); }
module cavity(extra=0) {
    rr(inside_w+2*extra,inside_l+2*extra,inside_r+extra);
}
module gland_profile() {
    difference() {
        cavity(gland_offset+gland_w/2);
        cavity(gland_offset-gland_w/2);
    }
}
module shell_profile() {
    outline();
}
// Short flat roof removes the extra upward freedom of the old teardrop apex.
// Width stays generous; the independently controlled height limits vertical play.
module pin_slot(h=$pin_fit_h) {
    intersection() {
        circle(d=pin_bore);
        square([pin_bore+eps,h],center=true);
    }
}
module axis_x(length) { rotate([90,0,90]) linear_extrude(length,center=true) children(); }
module hinge_knuckles(top=false) {
    spans=top ? [[-5.5,5.5]] : [[-15,-6],[6,15]];
    for(span=spans) translate([(span[0]+span[1])/2,hinge_y,hinge_z])
        axis_x(span[1]-span[0]) difference() {
            union() {
                circle(r=3);
                if(top) scale([1,-1])
                    polygon([[-5.5,-8],[-3.75,-8],[3,-1.25],[3,0],[-5.5,0]]);
                else polygon([[-5.5,-8],[-3.75,-8],[3,-1.25],[3,0],
                    [-3.5,0],[-3.5,seam_z-hinge_z],[-5.5,seam_z-hinge_z]]);
            }
            pin_slot();
        }
}
module open_lid(angle=open_angle) {
    translate([0,hinge_y,hinge_z]) rotate([-angle,0,0])
        translate([0,-hinge_y,-hinge_z]) lid();
}
module hinge_open_stop() {
    // Broad pedestal meets the rotating lid arm at 120 degrees, below the
    // knuckle's circular swept volume. Its underside grows at <=45 degrees.
    p=[3*cos(open_angle)+1.25*sin(open_angle),
       -3*sin(open_angle)+1.25*cos(open_angle)];
    q=[3*cos(open_angle),-3*sin(open_angle)];
    translate([0,hinge_y,hinge_z]) axis_x(6)
        polygon([[-5,-7.6],[-3.5,-7.6],[p[0],p[0]-4.1],p,q,[-5,q[1]]]);
}
module latch_frame(i) {
    rotate([0,0,[0,180,-90][i]])
        translate([(i==2?outside_l:outside_w)/2+3,0,latch_pin_z]) children();
}
module latch_mount() {
    // Two outside knuckles and a central positive parking stop; no wall holes.
    for(y=[-(clip_w/2+1.95),clip_w/2+1.95]) translate([0,y,0]) along_shaft(3.1) difference() {
        union() {
            circle(r=2.4);
            polygon([[-4.5,-6.7],[-3.3,-6.7],[2.4,-1],[2.4,0],
                     [-2.4,0],[-2.95,seam_z-latch_pin_z-0.02],
                     [-4.5,seam_z-latch_pin_z-0.02]]);
        }
        pin_slot();
    }
    // Lower root keeps the new stop's underside steeper than 45 degrees.
    along_shaft(3) polygon([[-4.5,-7.4],[-4.5,clip_stop_z+0.1],
        [clip_stop_u,clip_stop_z+0.1],[clip_stop_u,clip_stop_z-0.3]]);
}
module latch_catch() {
    // Positive horizontal bearing, with a 0.6-mm outer closing ramp.
    along_shaft(clip_w) polygon([[-4.2,catch_z-latch_pin_z-1.2],
        [catch_tip_u-0.4,catch_z-latch_pin_z-1.2],[catch_tip_u+0.6,catch_z-latch_pin_z-0.6],
        [catch_tip_u,catch_z-latch_pin_z],[hook_u,catch_z-latch_pin_z],
        [-3,lid_top-latch_pin_z-0.02],[-4.2,lid_top-latch_pin_z-0.02]]);
}
function beam_f(u)=let(s=(clip_arm_u-u)/(clip_arm_u-clip_beam_start)) s*s*(3-s)/2;
module clip_profile(lift=0,preload=clip_preload) {
    h=catch_z-latch_pin_z-preload;
    difference() {
        union() {
            circle(r=2.4);
            // Broad 2-mm frame with 1-mm root radii. Print this plane in XY.
            hull() { circle(r=1); translate([clip_arm_u,2.5]) circle(r=1); }
            hull() { translate([clip_arm_u,2.5]) circle(r=1);
                translate([clip_arm_u,h+1.5]) circle(r=1); }
            // Deflected state is a geometric cantilever approximation, not FEA.
            polygon(concat(
                [for(j=[0:40]) let(u=clip_beam_start+(clip_arm_u-clip_beam_start)*j/40)
                    [u,h+lift*beam_f(u)]],
                [for(j=[40:-1:0]) let(u=clip_beam_start+(clip_arm_u-clip_beam_start)*j/40)
                    [u,h+clip_t+lift*beam_f(u)]]));
            translate([hook_u,h+lift]) square([clip_hook_l,clip_hook_t]);
            translate([clip_arm_u,h+1.3]) offset(r=0.4)
                square([clip_tab_u-clip_arm_u,0.6]); // broad pull tab clears strap when parked
            translate([2.5,-1]) circle(r=0.65); // rests on the parking stop
        }
        pin_slot();
    }
}
module clip(lift=0,angle=0,preload=clip_preload) {
    rotate([0,angle,0]) along_shaft(clip_w) clip_profile(lift,preload);
}
module clip_print(preload=clip_preload) { linear_extrude(clip_w) clip_profile(0,preload); }
module clips(lift=clip_preload,angle=0) {
    for(i=[0:2]) latch_frame(i) clip(lift,angle);
}
module headed_pin(length) {
    // Final formed heads, not a printed pin. 0.4 mm axial running gap each end.
    along_shaft(length+0.8) circle(d=pin_d);
    for(s=[-1,1]) translate([0,s*(length/2+0.75),0]) along_shaft(0.7) circle(d=3.2);
}
module pins(rise=0) {
    translate([0,hinge_y,hinge_z+rise]) rotate([0,0,90]) headed_pin(30);
    for(i=[0:2]) latch_frame(i) translate([0,0,rise]) headed_pin(clip_mount_w);
}
module loaded_clip(play, lift, angle=0) {
    // Pin bears on the fixed slot roof; clip bears on the moving slot floor.
    // Rotation is about the ACTUAL raised pin, not the nominal journal centre.
    translate([0,0,play/2]) rotate([0,angle,0])
        translate([0,0,play/2]) clip(lift);
}
module loaded_clips(play,lift,angle=0) {
    for(i=[0:2]) latch_frame(i) loaded_clip(play,lift,angle);
}
module loaded_lid(play,angle=0) {
    translate([0,hinge_y,hinge_z+play/2]) rotate([-angle,0,0])
        translate([0,-hinge_y,-hinge_z+play/2]) lid();
}
module strap_ears() {
    for(s=[-1,1]) translate([s*(outside_w/2+3),strap_y,0])
        scale([s,1,1]) linear_extrude(4) strap_ear_profile(strap_slot_t);
}
module strap_ear_profile(gap) {
    difference() {
        rr(16,strap_w+strap_clear+7,3);
        translate([2.5,0]) rr(gap,strap_w+strap_clear,1.2);
    }
}
module strap_coupon() {
    // Three actual 4 mm-thick ear profiles on one labelled, connected strip.
    gaps=[3.5,5,6];
    difference() {
        linear_extrude(4) union() {
            for(i=[0:2]) translate([(i-1)*22,0]) strap_ear_profile(gaps[i]);
            translate([0,-26.5]) rr(64,7,1);
        }
        for(i=[0:2]) translate([(i-1)*22,-26.5,3.4])
            linear_extrude(0.6+eps) text(str(gaps[i]),size=3,halign="center",
                valign="center",font="Liberation Sans:style=Bold");
    }
}
module board_frame() { translate([board_x,board_y,0]) children(); }
pocket_wall = 1.2;
module pocket_outline(extra=0) {
    rr(pcb_w+2*pcb_clear+2*extra,pcb_l+2*pcb_clear+2*extra,1.9+pcb_clear+extra);
}
module tray_pocket() {
    // The board drops into this inset; its top is flush with the pocket rim.
    board_frame() {
        difference() {
            translate([0,0,tray_top-eps]) linear_extrude(pcb_top-tray_top+eps)
                difference() { pocket_outline(pocket_wall); pocket_outline(); }
            // Underside battery lead leaves toward the connector bay.
            translate([-2.5,-pcb_l/2-5,tray_top-1]) cube([5,5,10]);
            // No rim directly in front of the chip antenna body.
            translate([-4.5,pcb_l/2-1,tray_top-1]) cube([5.5,5,10]);
        }
        // Hard edge seats under the lid pads, joined to the rim. The underside
        // centre and battery pads stay open, exactly as on the fitted carrier.
        for(s=[-1,1]) scale([s,1,1])
            translate([pcb_w/2-0.8,clamp_y-3.5,tray_top-eps])
                cube([0.8+pcb_clear+eps,7,pcb_under-tray_top+eps]);
    }
}
module battery_fences() {
    translate([battery_x,battery_y,floor_t-eps])
    for(s=[-1,1]) {
        // Short fences allow seam/protection leads to leave at either end.
        translate([s*(battery_w/2+battery_xy_clear+0.5),-battery_protection_extra/2,0])
            linear_extrude(2+eps) rr(1, battery_l+battery_protection_extra-8,0.4);
        translate([0,s*(battery_l/2+battery_xy_clear+0.5)-(s==-1?battery_protection_extra:0),0])
            // 0.35 avoids a tangent arc vertex exactly on the cavity wall.
            linear_extrude(2+eps) rr(battery_w-8,1,0.35);
    }
}
module wire_anchor(x,y) {
    translate([x,y,tray_top-eps]) difference() {
        linear_extrude(4+eps) rr(7,5,1);
        // 2.8 mm cable-tie tunnel; completely above the intact floor.
        translate([-1.4,-3,1.2]) cube([2.8,6,1.6]);
    }
}
module tray_body_2d() {
    difference() {
        rr(2*tray_body_x,2*tray_body_y,3);
        // Front notch lets the cell lead rise without running through the seam.
        translate([-5,-23]) square([10,10]);
    }
    // Rigid root blocks: the only joint between the body and each spring arm.
    for(s=[-1,1]) translate([s*(tray_body_x+arm_slot/2),0])
        square([arm_slot+0.8,2*arm_root],center=true);
}
module tab(y) {
    // Snap tab outboard of the arm, from axis-aligned hulls (exact coordinates,
    // so its faces merge cleanly with the arm's). Lower lead-in ramp is 31
    // degrees from vertical (printable); the upper outer corner meets the
    // 45-degree pocket ceiling, so a firm pull releases the tray without tools.
    // 0.1 mm short of the beam ends at each side: no coincident end faces.
    w=inside_w/2+tab_reach;
    a=arm_x1-0.3;
    hull() {
        translate([a,y-tab_l/2+0.1,tray_z]) cube([w-0.6-a,tab_l-0.2,arm_t]);
        translate([a,y-tab_l/2+0.1,tray_z+tab_lead]) cube([w-a,tab_l-0.2,arm_t-tab_lead]);
    }
}
module tray_arm(drop=0) {
    // +X arm, both ends. Printed in the bottom layers, so it bends in Z along
    // its layers (hold-down spring) and in X within them (snap). drop>0 shears
    // the beam: root follows the body down, the tab tip stays on its pedestal.
    // A straight-line approximation of the loaded cantilever, not FEA.
    y1=tab_y-tab_l/2;
    y2=tab_y+tab_l/2;
    if(drop==0) translate([arm_x0,-y2,tray_z]) cube([arm_w,2*y2,arm_t]);
    for(e=[-1,1]) scale([1,e,1]) {
        if(drop!=0) {
            translate([arm_x0,0,tray_z-drop]) cube([arm_w,arm_root,arm_t]);
            multmatrix([[1,0,0,0],[0,1,0,0],[0,drop/(y1-arm_root),1,-drop*y1/(y1-arm_root)],[0,0,0,1]])
                translate([arm_x0,arm_root,tray_z]) cube([arm_w,y1-arm_root,arm_t]);
            translate([arm_x0,y1,tray_z]) cube([arm_w,tab_l,arm_t]);
        }
        tab(tab_y);
    }
}
// drop: lid-closed descent of the body; defl: inward snap deflection of the arms.
module tray(drop=0,defl=0) {
    translate([0,0,-drop]) {
        translate([0,0,tray_z]) linear_extrude(tray_t) tray_body_2d();
        tray_pocket();
        wire_anchor(11,-17.5);
        wire_anchor(-11,-15);
    }
    for(s=[-1,1]) scale([s,1,1]) translate([-defl,0,0]) tray_arm(drop);
}
module tray_print() { translate([0,0,-tray_z]) tray(); }
module tray_pedestals() {
    for(s=[-1,1]) scale([s,1,1]) {
        // Ledges under the tab ends: the springs react here, not on the snap.
        for(e=[-1,1]) translate([arm_x0+0.3,e*tab_y-1.5,floor_t-eps])
            cube([inside_w/2-arm_x0-0.3+eps,3,tray_z-floor_t+eps]);
        // Over-travel stop under the rigid root: the body can never reach the
        // pack's growth reserve, whatever the tolerance stack does.
        translate([arm_x0+0.3,-1.5,floor_t-eps])
            cube([inside_w/2-arm_x0-0.3+eps,3,tray_z-tray_travel-floor_t+eps]);
    }
}
module tray_pockets() {
    // Retaining pockets in the side walls, below the gland. Flat floor, 45-degree
    // ceiling (printable overhang, and the release cam).
    for(s=[-1,1],e=[-1,1]) scale([s,1,1]) translate([inside_w/2,e*tab_y,0])
        rotate([90,0,0]) linear_extrude(tab_l+0.6,center=true)
            polygon([[-eps,tray_z-0.2],[groove_d,tray_z-0.2],[groove_d,groove_ceil],
                     [-eps,groove_ceil+groove_d+eps]]);
}
module base() {
    difference() {
        union() {
            difference() {
                linear_extrude(seam_z) shell_profile();
                translate([0,0,floor_t]) linear_extrude(seam_z) cavity();
                translate([0,0,seam_z-gland_d])
                    linear_extrude(gland_d+eps) gland_profile();
                tray_pockets();
            }
            strap_ears();
            tray_pedestals();
            battery_fences();
            hinge_knuckles();
            hinge_open_stop();
            for(i=[0:2]) latch_frame(i) latch_mount();
        }
    }
}
// The cap is defined in assembly coordinates; export is a true rotation.
module lid_pads() {
    // Rigid pads on the bare edge lands, directly above the tray's edge seats,
    // where the old screw clamps pressed. The spring is in the tray arms, so
    // the lid still closes onto its hard lands whatever the stack tolerance.
    // A wider root clears the pocket rim by 0.8 mm; it prints roof-down.
    board_frame() for(s=[-1,1]) scale([s,1,1]) {
        translate([pad_u[0],clamp_y-pad_v/2,pcb_top_closed])
            cube([pad_u[1]-pad_u[0],pad_v,0.8+eps]);
        translate([pad_u[0],clamp_y-pad_v/2,pcb_top_closed+0.8])
            cube([pcb_w/2+pcb_clear+pocket_wall+0.5-pad_u[0],pad_v,
                  lid_top-roof_t-pcb_top_closed-0.8+eps]);
    }
}
module lid() {
    if($lid_part!="pads") lid_shell();
    if($lid_part!="shell") lid_pads();
}
module lid_shell() {
    difference() {
        translate([0,0,seam_z]) linear_extrude(lid_h) shell_profile();
        translate([0,0,seam_z-eps])
            linear_extrude(lid_h-roof_t+eps) cavity();
        // Broad inside recess covers RGB and charging LED beside USB.
        translate([board_x+5.7,board_y-7.7,lid_top-roof_t-eps])
            linear_extrude(roof_t-led_skin+eps) rr(8,8,1.5);
        translate([8,-12,lid_top-0.4]) linear_extrude(0.4+eps)
            text(role,size=4,halign="center",valign="center",font="Liberation Sans:style=Bold");
        // Physical +Y datum; do not infer the IMU chip's axes from it.
        translate([0,12,lid_top-0.4]) linear_extrude(0.4+eps)
            polygon([[-1,-4],[1,-4],[1,1],[3,1],[0,5],[-3,1],[-1,1]]);
    }
    hinge_knuckles(true);
    for(i=[0:2]) latch_frame(i) latch_catch();
}
module lid_print() { translate([0,0,lid_top]) rotate([180,0,0]) lid(); }
module electronics(drop=0) {
    // Deliberately simplified fit envelopes, not vendor component CAD.
    // drop: board and connector ride down with the tray when the lid closes.
    translate([0,0,-drop]) board_frame() {
        color("SeaGreen") translate([0,0,pcb_under])
            linear_extrude(pcb_t) rr(pcb_w,pcb_l,1.9);
        color("Silver") translate([-4.5,-11.2,pcb_top]) cube([9,7.5,component_h]);
        color("Gold") translate([-3.3983,8.6056,pcb_top]) cube([3.2,1.6,1.04]);
        color("Lime") translate([5.7,-7.7,pcb_top]) cylinder(d=1.6,h=0.8);
        color("Red") translate([5.715,-9.8425,pcb_top]) cylinder(d=1,h=0.5);
    }
    color("Silver") translate([battery_x-battery_w/2,battery_y-battery_l/2,
                               floor_t+battery_tape]) cube([battery_w,battery_l,battery_t]);
    if(battery_protection_extra>0)
        color("SteelBlue") translate([battery_x-battery_w/2,battery_y-battery_l/2-battery_protection_extra,
                                      floor_t+battery_tape])
            cube([battery_w,battery_protection_extra,battery_t]);
    color("Ivory") translate([conn_x-connector_w/2,conn_y-connector_l/2,tray_top-drop])
        cube([connector_w,connector_l,connector_h]);
}
module battery_reserve() {
    // Tolerance + growth, including the entire provisional protection extension.
    translate([-battery_w/2-battery_xy_clear,
               battery_y-battery_l/2-battery_protection_extra-battery_xy_clear,
               floor_t+battery_tape])
        cube([battery_w+2*battery_xy_clear,
              battery_l+battery_protection_extra+2*battery_xy_clear,
              battery_t+battery_growth]);
}
module solder_wire_reserve() {
    // Two underside pads plus an inward/forward lead path clear of edge stops.
    translate([-6,board_y-3.5,pcb_under-2]) cube([4,5,2]);
    translate([-6,board_y-3.5,pcb_under-2]) cube([7.5,2,1.5]);
    translate([-1.5,-3,pcb_under-2]) cube([3,board_y+2.5,1.5]);
    // Low front run from the tray notch toward the connector bay.
    translate([-1.5,-17,tray_top]) cube([8.5,3,2]);
}
module underside_components() {
    // Provisional populated underside, inboard of the two bare edge seats.
    translate([board_x-7,board_y-8.5,pcb_under-2.2]) cube([14,17,2.2]);
}
module usb_corridor() {
    translate([board_x-6,-60,pcb_top+1.6-3.5])
        cube([12,60+board_y-16,7]);
    translate([board_x-4.5,board_y-16,pcb_top]) cube([9,4.8,component_h]);
}
module gasket_preview() {
    color("DarkSlateGray") translate([0,0,seam_z-gland_d])
        linear_extrude(cord_d) difference() {
            cavity(gland_offset+cord_d/2);
            cavity(gland_offset-cord_d/2);
        }
}
module assembly(explode=0) {
    color([0.4,0.7,0.8,0.65]) base();
    electronics(explode?0:tray_preload);
    color([0.55,0.72,0.9,0.6]) tray(explode?0:tray_preload);
    gasket_preview();
    translate([0,0,explode]) color([0.7,0.85,0.9,0.55]) lid();
    color("OrangeRed") clips();
    color("Ivory") pins();
}
module opened_assembly(angle=open_angle) {
    color([0.4,0.7,0.8,0.65]) base();
    color([0.55,0.72,0.9,0.6]) tray();
    electronics();
    color([0.7,0.85,0.9,0.55]) open_lid(angle);
    color("OrangeRed") clips(0,clip_park);
    color("Ivory") pins();
    color([0.3,0.3,0.3,0.3]) usb_corridor();
}
module closure_coupon_base() {
    union() {
        translate([0,12,0]) intersection() {
            base(); translate([-14,-45,0]) cube([28,25,30]);
        }
        translate([0,-12,0]) intersection() {
            base(); translate([-16,22,0]) cube([32,15,30]);
        }
        translate([-14,-10,0]) cube([28,23,floor_t]);
        translate([9,-10,0]) cube([13,20,floor_t]);
        for(j=[0:2]) translate([17,(j-1)*6,0]) difference() {
            translate([-5,-2,0]) cube([10,4,8]);
            // Common 4.2-mm floor; roofs 6.0 / 6.2 / 6.4 match 0.2-mm layers.
            translate([0,0,4.2+[1.8,2.0,2.2][j]/2]) axis_x(11)
                pin_slot([1.8,2.0,2.2][j]);
            translate([0,0,7.6]) linear_extrude(0.5)
                text(str([1.8,2.0,2.2][j]),size=2,halign="center",valign="center");
        }
    }
}
module closure_coupon_lid() {
    union() {
        translate([0,12,0]) intersection() {
            lid(); translate([-14,-40,0]) cube([28,19,30]);
        }
        translate([0,-12,0]) intersection() {
            lid(); translate([-16,22,0]) cube([32,15,30]);
        }
        translate([-14,-12,lid_top-roof_t]) cube([28,25,roof_t]);
    }
}
module closure_coupon_lid_print() {
    translate([0,0,lid_top]) rotate([180,0,0]) closure_coupon_lid();
}
module closure_coupon_assembly() {
    color("LightSteelBlue") closure_coupon_base();
    color([0.7,0.85,0.9,0.55]) closure_coupon_lid();
    color("OrangeRed") translate([0,12,0]) latch_frame(2) clip(clip_preload);
    color("Ivory") {
        translate([0,hinge_y-12,hinge_z]) rotate([0,0,90]) headed_pin(30);
        translate([0,12,0]) latch_frame(2) headed_pin(clip_mount_w);
    }
}
module battery_gauge() {
    // Cell + extra protection-end length + per-side allowance, open at top.
    pack_l=battery_l+battery_protection_extra;
    difference() {
        linear_extrude(1.2+battery_t+battery_growth)
            rr(battery_w+2*battery_xy_clear+4,pack_l+2*battery_xy_clear+4,2);
        translate([0,0,1.2]) linear_extrude(battery_t+battery_growth+eps)
            square([battery_w+2*battery_xy_clear,pack_l+2*battery_xy_clear],center=true);
        // Wire exit, not intended to gauge the connector itself.
        translate([-5,0,1.2]) cube([10,pack_l,12]);
    }
}
module board_coupon() {
    // The tray's actual board pocket, seats and rim, cropped clear of the arms.
    intersection() {
        translate([-board_x,-board_y,-tray_z]) tray();
        translate([-14,-14,0]) cube([28,28,12]);
    }
}
module tray_coupon() {
    // The base's actual +Y tab pockets, pedestals, stop and full-height walls,
    // open at Y=12.5. The real tray's +Y tabs snap in; its -Y half overhangs.
    intersection() {
        base();
        translate([-outside_w/2,12.5,0]) cube([outside_w,outside_l/2-12.5-0.1,seam_z+1]);
    }
}
module seal_coupon() {
    // Preserve the original 24x11x6 coupon: same gland and nut AF; this is a
    // compression/fit gauge, not a coupon of the new deeper case nut recess.
    difference() {
        union() {
            translate([-12,0,0]) cube([24,7,6]);
            intersection() {
                translate([0,-0.5,0]) cylinder(r=4.5,h=6);
                translate([-12,-4,0]) cube([24,11,6]);
            }
        }
        translate([-12-eps,3,4.5]) cube([24+2*eps,2.4,1.5+eps]);
        translate([0,-0.5,-eps]) {
            cylinder(d=shell_pilot,h=6+2*eps);
            cylinder(d=6.5,h=3.4+eps,$fn=6);
        }
    }
}
module seal_coupon_lid() {
    difference() {
        translate([0,1.5,0]) linear_extrude(3) square([24,11],center=true);
        translate([0,-0.5,-eps]) cylinder(d=shell_pilot,h=3+2*eps);
    }
}
// Profiles use [X,Z]; the channel and cylindrical shaft run along Y.
module along_shaft(length) {
    rotate([90,0,0]) linear_extrude(length,center=true) children();
}
module saddle_profile() {
    // Bottom corners are rounded BELOW z=0 then cropped. This preserves the
    // 45-degree growing shoulders and a genuinely flat, support-free bed face.
    intersection() {
        offset(r=saddle_edge_r) offset(delta=-saddle_edge_r)
            polygon([[-saddle_w/2,(saddle_w-saddle_contact_w)/2],
                     [-saddle_contact_w/2+2*saddle_edge_r,-2*saddle_edge_r],
                     [saddle_contact_w/2-2*saddle_edge_r,-2*saddle_edge_r],
                     [saddle_w/2,(saddle_w-saddle_contact_w)/2],
                     [saddle_w/2,saddle_high],[0,saddle_web],
                     [-saddle_w/2,saddle_high]]);
        translate([-saddle_w,0]) square([2*saddle_w,saddle_high+1]);
    }
}
module saddle() {
    difference() {
        intersection() {
            along_shaft(saddle_l) saddle_profile();
            linear_extrude(saddle_high+1) rr(saddle_w,saddle_l,3);
        }
        for(s=[-1,1]) {
            translate([s*saddle_slot_x,0,-eps])
                linear_extrude(saddle_high+2) rr(strap_slot_t,strap_w+strap_clear,1.2);
            // Round over the shaft-side strap mouth in its sloping V plane.
            // A shear preserves the vertical slot walls; the rounded cut is
            // a convex profile, so the library's hull loft is appropriate.
            translate([s*saddle_slot_x,0,saddle_web+saddle_slot_x*saddle_slope])
                multmatrix([[1,0,0,0],[0,1,0,0],[s*saddle_slope,0,1,0],[0,0,0,1]])
                    edge_extrude(h=2+eps,z0=-2,top=-0.8,style="round")
                        rr(strap_slot_t,strap_w+strap_clear,1.2);
        }
        // Break the ends of both contact faces: no sharp transverse V lip.
        for(s=[-1,1]) hull() {
            translate([0,s*(saddle_l/2-0.8),0]) along_shaft(eps)
                polygon([[-50,saddle_web+50*saddle_slope],[0,saddle_web],
                         [50,saddle_web+50*saddle_slope],[50,80],[-50,80]]);
            translate([0,s*(saddle_l/2+eps),-0.8]) along_shaft(eps)
                polygon([[-50,saddle_web+50*saddle_slope],[0,saddle_web],
                         [50,saddle_web+50*saddle_slope],[50,80],[-50,80]]);
        }
    }
}
module saddle_installed() {
    translate([0,strap_y,-case_grip_t]) rotate([180,0,0]) children();
}
module saddle_liners() {
    // Two separate firm rubber strips; do not fold a thick pad into the apex.
    for(s=[-1,1]) scale([s,1,1]) along_shaft(saddle_l-6)
        polygon([[3,saddle_web+3*saddle_slope],[21,saddle_web+21*saddle_slope],
                 [21,saddle_web+21*saddle_slope+saddle_liner/sin(saddle_angle/2)],
                 [3,saddle_web+3*saddle_slope+saddle_liner/sin(saddle_angle/2)]]);
}
module shaft_envelope(d=shaft_d,liner=saddle_liner,inflate=false) {
    translate([0,0,saddle_web+(d/2+liner)/sin(saddle_angle/2)])
        rotate([90,0,0]) cylinder(r=d/2+(inflate?liner:0),h=100,center=true,$fn=128);
}
module saddle_assembly(d=shaft_d) {
    assembly();
    color("DarkSlateGray") translate([-(saddle_contact_w-2)/2,strap_y-23,-case_grip_t])
        cube([saddle_contact_w-2,46,case_grip_t]);
    saddle_installed() {
        color([0.35,0.6,0.75,0.8]) saddle();
        color("Teal") saddle_liners();
        color([0.5,0.5,0.5,0.65]) shaft_envelope(d);
    }
}
function lower_tangent_angle(p,zc,r) =
    atan2(p[1]-zc,p[0])+acos(r/norm([p[0],p[1]-zc]));
function lower_arc(zc,r,a,b) =
    [for(i=[0:48]) let(t=a+(b-a)*i/48) [r*cos(t),zc+r*sin(t)]];
module strap_route(d=shaft_d) {
    // Illustrative 2 mm-thick band, NOT a measured Trilancer thickness.
    // Two under-shaft passes and outside-ear turns leave BOTH lid and flat
    // case/saddle contact untouched. Small free gaps represent an untensioned
    // routing envelope; compression/friction still require physical validation.
    t=2;
    zc=saddle_web+(d/2+saddle_liner)/sin(saddle_angle/2);
    ri=d/2+t/2+0.2;
    ro=ri+t+0.3;
    pin=[saddle_slot_x,saddle_web+saddle_slot_x*saddle_slope+1.5];
    pout=[saddle_w/2+3,saddle_high+3];
    ex=ear_slot_x;
    ox=ear_outer_x+t/2+0.2;
    pre=max(1.5,saddle_slot_x-saddle_contact_w/2-3);
    ai=lower_tangent_angle(pin,zc,ri);
    ao=lower_tangent_angle(pout,zc,ro);
    assert(norm([pin[0],pin[1]-zc])>ri, "Strap needs room to bend around shaft");
    pts=concat([[-pin[0],pin[1]],[-saddle_slot_x,pre],[-ex,1.5],
                [-ex,-5.2-case_grip_t],[-ox,-5.2-case_grip_t],
                [-ox,2],[-pout[0],pout[1]]],
               lower_arc(zc,ro,180-ao,ao),
               [pout,[ox,2],[ox,-5.2-case_grip_t],
                [ex,-5.2-case_grip_t],[ex,1.5],[saddle_slot_x,pre],pin],
               lower_arc(zc,ri,ai,180-ai));
    along_shaft(strap_w) union() {
        for(i=[0:len(pts)-1]) hull() {
            translate(pts[i]) circle(r=t/2,$fn=24);
            translate(pts[(i+1)%len(pts)]) circle(r=t/2,$fn=24);
        }
    }
}
module route_slice() {
    // Re-extrude the section so OpenCSG doesn't paint every clipping face in
    // its uniform Boolean-cut colour (which would hide the strap colour key).
    rotate([-90,0,0]) linear_extrude(0.2)
        projection(cut=true) rotate([90,0,0]) children();
}
module strap_route_section(released=false) {
    // Colours outside Boolean operations keep the cut faces legible in F5 PNGs.
    color("LightSteelBlue") route_slice() union() { base(); lid(); }
    color("SteelBlue") route_slice() saddle_installed() saddle();
    color("Teal") route_slice() saddle_installed() saddle_liners();
    color("Gray") route_slice() saddle_installed() shaft_envelope();
    color("DarkSlateGray") translate([-(saddle_contact_w-2)/2,-0.1,-case_grip_t])
        cube([saddle_contact_w-2,0.2,case_grip_t]);
    color("DarkOrange") route_slice() saddle_installed() strap_route();
    color("OrangeRed") route_slice() clips(released?0:clip_preload,released?clip_park:0);
}
module empty_check(label) {
    v=volume();
    echo(check=label,intersection_mm3=v);
    assert(v<0.001,str(label," interference: ",v," mm3"));
    children();
}
module positive_check(label) {
    v=volume(); echo(check=label,intentional_intersection_mm3=v);
    assert(v>0.01,str(label," must have positive engagement")); children();
}
module closure_checks() {
    dfm_report() clip_print();
    empty_check("closed clips/base + lid") intersection() {
        clips(); union() { base(); lid(); }
    }
    empty_check("headed pins/all mating parts") intersection() {
        pins(); union() { base(); lid(); clips(); }
    }
    positive_check("free hook overlap requires 0.2 mm elastic lift") intersection() {
        clips(0); lid();
    }
    positive_check("outboard hook bearing seats against inward rotation") intersection() {
        clips(clip_preload,-2); lid();
    }
    positive_check("clip park stop blocks 64 degrees") intersection() {
        clips(0,clip_park+2); base();
    }
    positive_check("hinge opening stop blocks 122 degrees") intersection() {
        open_lid(open_angle+2); base();
    }
    empty_check("parked clips/open USB corridor") intersection() { clips(0,clip_park); usb_corridor(); }
    empty_check("10 mm finger-pad approach to all closed tabs") intersection() {
        for(i=[0:2]) latch_frame(i)
            translate([clip_tab_u+5.4,0,catch_z-latch_pin_z-clip_preload+1.6])
                along_shaft(8) circle(d=10);
        union() { base(); lid(); clips(); pins();
            for(d=[25,40,60]) saddle_installed() strap_route(d); }
    }
    for(d=[25,40,60])
        empty_check(str("closed clips and mount/strap d=",d)) intersection() {
            union() { clips(); base(); }
            saddle_installed() strap_route(d);
        }
    // Release: lift hook to 0.20 above catch, swing clear, relax, park on stop.
    for(a=[0:2:30]) empty_check(str("clip lifted release a=",a)) intersection() {
        clips(clip_release,a); union() { base(); lid(); pins(); }
    }
    for(a=[30:2:clip_park]) empty_check(str("clip free parking a=",a)) intersection() {
        clips(0,a);
        union() { base(); lid(); pins();
            for(d=[25,40,60]) saddle_installed() strap_route(d); }
    }
    empty_check("closure coupon mating") intersection() { closure_coupon_base(); closure_coupon_lid(); }
    empty_check("closure coupon closed clip") intersection() {
        translate([0,12,0]) latch_frame(2) clip(clip_preload);
        union() { closure_coupon_base(); closure_coupon_lid(); }
    }
    // Assembly before pins: lower the lid into the interleaved knuckles, then
    // slide each loose clip radially into its mounting gap with the lid open.
    for(z=[0:2:10]) empty_check(str("lid assembly insertion z=",z)) intersection() {
        translate([0,0,z]) lid(); base();
    }
    for(u=[0:2:14]) empty_check(str("clip radial installation u=",u)) intersection() {
        for(i=[0:2]) latch_frame(i) translate([u,0,0]) clip();
        union() { base(); open_lid(); }
    }
    empty_check("straight unheaded pin insertion corridors") intersection() {
        union() {
            translate([0,hinge_y,hinge_z]) axis_x(90) circle(d=pin_d);
            for(i=[0:2]) latch_frame(i) along_shaft(90) circle(d=pin_d);
        }
        union() { base(); lid(); clips(); }
    }
}
module motion_obstacles() {
    base(); tray(); electronics();
    pins(); clips(0,clip_park);
    for(d=[25,40,60]) saddle_installed() strap_route(d);
    saddle_installed() saddle();
}
module motion_checks() {
    // One-degree discrete sweep, with all hinge pins and parked clips installed.
    // The shell sweeps past the FREE (sprung-up) internals. The pads hold the
    // board down until they lift away, so they sweep past the CLOSED board,
    // then must be clear of the free board once they have risen past preload.
    for(a=[0:1:open_angle]) empty_check(str("lid sweep degrees=",a)) intersection() {
        open_lid(a,$lid_part="shell"); motion_obstacles();
    }
    for(a=[0:1:open_angle]) empty_check(str("lid pads over closed board degrees=",a)) intersection() {
        open_lid(a,$lid_part="pads"); union() { base(); tray(tray_preload); electronics(tray_preload); }
    }
    for(a=[2:1:open_angle]) empty_check(str("lid pads over free board degrees=",a)) intersection() {
        open_lid(a,$lid_part="pads"); union() { tray(); electronics(); }
    }
    empty_check("fully open lid/USB cable and connector nose") intersection() {
        open_lid(open_angle); usb_corridor();
    }
}
module loaded_fit_checks() {
    echo(fit_budget="vertical paired-journal lift",
         old_clip_teardrop_mm=round_pin_slop*(1+sqrt(2)),
         old_hinge_teardrops_mm=2*round_pin_slop*sqrt(2),
         new_nominal_mm=pin_fit_h-pin_d, finished_limit_mm=pin_play_limit);
    // The larger slot is a simulated manufacturing limit, not another print
    // recommendation. Full assembly coupons must measure <=0.10 mm paired lift.
    for(play=[pin_fit_h-pin_d,pin_play_limit]) let($pin_fit_h=pin_d+play) {
        echo(fit_budget="loaded closure", play_mm=play,
             residual_preload_mm=clip_preload-play,
             minimum_rigid_seal_squeeze_percent=100*(cord_d-gland_d-play)/cord_d,
             free_spring_strain_percent=100*1.5*clip_t*(clip_preload-play)/pow(clip_arm_u-max(clip_beam_start,hook_u+clip_hook_l),2));
        assert(clip_preload-play>=0.099,"No free lifting deadband before clip force");
        empty_check(str("loaded clips, lid ON lands, play=",play)) intersection() {
            loaded_clips(play,clip_preload-play);
            union() { base(); lid(); pins(play/2); }
        }
        empty_check(str("loaded rigid lid and clips, seal gap=",play)) intersection() {
            loaded_lid(play);
            union() { base(); loaded_clips(play,clip_preload); pins(play/2); }
        }
        positive_check(str("clip bearing limits further rise, play=",play)) intersection() {
            translate([0,0,0.02]) loaded_clips(play,0);
            pins(play/2);
        }
        positive_check(str("hinge bearing limits further rise, play=",play)) intersection() {
            translate([0,0,0.02]) loaded_lid(play);
            pins(play/2);
        }
        // Simultaneous sideways bearing extremes within the circular width.
        // The remaining hook overlap must carry load even when journals wander.
        for(side=[-1,1]) let(shift=side*sqrt(pow(round_pin_slop,2)-pow(play/2,2))) {
            echo(fit_budget="lateral bearing", paired_side_shift_mm=2*shift,
                 minimum_hook_overlap_mm=catch_tip_u-max(hook_u,hook_u+2*shift));
            empty_check(str("loaded clip lateral pin/base clearance play=",play," side=",side)) intersection() {
                for(i=[0:2]) latch_frame(i) translate([2*shift,0,play])
                    clip(clip_preload-play);
                union() { base();
                    for(i=[0:2]) latch_frame(i) translate([shift,0,play/2]) headed_pin(clip_mount_w); }
            }
            if(side>0) empty_check(str("loaded outward clip/lid clearance play=",play)) intersection() {
                for(i=[0:2]) latch_frame(i) translate([2*shift,0,play])
                    clip(clip_preload-play);
                lid();
            }
            // Inward translation is physically stopped by the catch's rising
            // shoulder. It is a blocked pose, not an allowed interference.
            positive_check(str(side<0?"catch blocks inward lateral drift play=":
                "outward lateral hook engagement play=",play)) intersection() {
                for(i=[0:2]) latch_frame(i) translate([2*shift,0,play])
                    clip(clip_preload-play);
                translate([0,0,side>0?0.02:0]) lid();
            }
        }
        for(a=[0:2:30]) empty_check(str("loaded clip release play=",play," a=",a)) intersection() {
            loaded_clips(play,clip_release-play,a);
            union() { base(); lid(); pins(play/2); }
        }
        for(a=[30:2:clip_park]) empty_check(str("loaded clip parking play=",play," a=",a)) intersection() {
            loaded_clips(play,0,a);
            union() { base(); lid(); pins(play/2);
                for(d=[25,40,60]) saddle_installed() strap_route(d); }
        }
        for(a=[0:1:open_angle]) empty_check(str("loaded lid sweep play=",play," a=",a)) intersection() {
            loaded_lid(play,a,$lid_part="shell");
            union() { base(); tray(); electronics();
                pins(play/2); loaded_clips(play,0,clip_park);
                for(d=[25,40,60]) saddle_installed() strap_route(d);
                saddle_installed() saddle(); }
        }
        empty_check(str("loaded fully open USB clearance play=",play)) intersection() {
            union() { loaded_lid(play,open_angle); loaded_clips(play,0,clip_park); }
            usb_corridor();
        }
    }
}
module geometry_checks() {
    dfm_report() base();
    dfm_report() lid_print();
    empty_check("base/lid") intersection() { base(); lid(); }
    for(d=[0,tray_preload,tray_travel]) {
        empty_check(str("base/electronics drop=",d)) intersection() { base(); electronics(d); }
        empty_check(str("tray/base drop=",d)) intersection() { tray(d); base(); }
        empty_check(str("tray/electronics drop=",d)) intersection() { tray(d); electronics(d); }
        empty_check(str("battery tolerance + growth/tray drop=",d)) intersection() {
            battery_reserve(); tray(d); }
    }
    empty_check("lid/closed board at nominal preload") intersection() { lid(); electronics(tray_preload); }
    positive_check("lid pads preload the free board") intersection() { lid(); electronics(); }
    empty_check("lid shell/free board and components") intersection() {
        lid($lid_part="shell"); electronics(); }
    empty_check("lid/free tray: only the board takes pad load") intersection() { lid(); tray(); }
    empty_check("lid/tray at full travel") intersection() { lid(); tray(tray_travel); }
    positive_check("over-travel stop blocks the body beyond full travel") intersection() {
        tray(tray_travel+0.05); base(); }
    positive_check("tab pockets retain a lifted tray") intersection() {
        translate([0,0,0.4]) tray(); base(); }
    positive_check("undeflected tabs cannot pass the wall") intersection() {
        translate([0,0,seam_z-tray_z-1]) tray(); base(); }
    for(z=[0:0.25:seam_z-tray_z+0.5]) empty_check(str("snap insertion, arms in by tab reach, z=",z))
        intersection() { translate([0,0,z]) tray(0,tab_reach); base(); }
    dfm_report() tray_print();
    empty_check("battery tolerance + growth/base") intersection() { battery_reserve(); base(); }
    empty_check("underside solder + wire/tray") intersection() { solder_wire_reserve(); tray(); }
    empty_check("underside solder + wire/base+lid") intersection() {
        solder_wire_reserve(); union() { base(); lid(); }
    }
    empty_check("populated underside/tray") intersection() { underside_components(); tray(); }
    empty_check("USB cable over rim, lid open, free tray") intersection() {
        union() { base(); tray(); electronics(); }
        usb_corridor();
    }
    let(E=2000, Iz=arm_w*pow(arm_t,3)/12, Ix=arm_t*pow(arm_w,3)/12,
        kz=3*E*Iz/pow(arm_l,3), kx=3*E*Ix/pow(arm_l,3))
        echo(spring_budget="tray arms, simple cantilever, PETG E=2000 MPa, not FEA",
             arm_length_mm=arm_l, four_arm_rate_N_per_mm=4*kz,
             hold_down_N_min_nom_max=[4*kz*(tray_preload-0.3),4*kz*tray_preload,4*kz*(tray_preload+0.3)],
             strain_percent_at_full_travel=100*3*arm_t*tray_travel/(2*arm_l*arm_l),
             snap_force_per_tab_N=kx*tab_reach,
             snap_strain_percent=100*3*arm_w*tab_reach/(2*arm_l*arm_l),
             pull_out_estimate_N_total_mu03=4*kx*tab_reach*1.3/0.7);
    dfm_report() saddle();
    empty_check("saddle/base") intersection() { base(); saddle_installed() saddle(); }
    // Effective circle is offset by the liner thickness normal to both faces.
    // Check the actual CSG over the provisional range, not just V arithmetic.
    for(d=[25,40,55,60], liner=[0.5,1,1.5])
        empty_check(str("saddle/lined cylinder d=",d," liner=",liner))
            intersection() { saddle(); shaft_envelope(d,liner,true); }
    for(d=[25,40,60]) {
        empty_check(str("2 mm strap route/base+lid d=",d)) intersection() {
            union() { base(); lid(); }
            saddle_installed() strap_route(d);
        }
        empty_check(str("2 mm strap route/saddle d=",d)) intersection() {
            saddle(); strap_route(d);
        }
        empty_check(str("2 mm strap route/shaft d=",d)) intersection() {
            shaft_envelope(d); strap_route(d);
        }
        empty_check(str("2 mm strap route/rubber d=",d)) intersection() {
            saddle_liners(); strap_route(d);
        }
    }
}
if(part=="base") base();
else if(part=="lid") lid_print();
else if(part=="tray") tray_print();
else if(part=="tray_coupon") tray_coupon();
else if(part=="battery_gauge") battery_gauge();
else if(part=="board_coupon") board_coupon();
else if(part=="seal_coupon") seal_coupon();
else if(part=="seal_coupon_lid") seal_coupon_lid();
else if(part=="saddle") saddle();
else if(part=="strap_coupon") strap_coupon();
else if(part=="clip") clip_print();
else if(part=="clip_loose") clip_print(0.1);
else if(part=="clip_tight") clip_print(0.3);
else if(part=="closure_coupon_base") closure_coupon_base();
else if(part=="closure_coupon_lid") closure_coupon_lid_print();
else if(part=="closure_coupon") closure_coupon_assembly();
else if(part=="opened") opened_assembly();
else if(part=="latch_detail") {
    color("LightSteelBlue") latch_mount();
    color([0.7,0.85,0.9,0.6]) latch_catch();
    color("OrangeRed") clip(clip_preload);
    color("Ivory") headed_pin(clip_mount_w);
}
else if(part=="latch_released") {
    color("LightSteelBlue") latch_mount();
    color([0.7,0.85,0.9,0.6]) latch_catch();
    color("OrangeRed") clip(0,clip_park);
    color("Ivory") headed_pin(clip_mount_w);
}
else if(part=="latch_section") {
    color("LightSteelBlue") route_slice() latch_mount();
    color("SeaGreen") route_slice() latch_catch();
    color("OrangeRed") route_slice() clip(clip_preload);
    color("Ivory") route_slice() headed_pin(clip_mount_w);
}
else if(part=="loaded_latch") {
    play=pin_fit_h-pin_d;
    color("LightSteelBlue") route_slice() latch_mount();
    color("SeaGreen") route_slice() latch_catch();
    color("OrangeRed") route_slice() loaded_clip(play,clip_preload-play);
    color("Ivory") route_slice() translate([0,0,play/2]) headed_pin(clip_mount_w);
}
else if(part=="hinge_detail") {
    color("LightSteelBlue") { hinge_knuckles(); hinge_open_stop(); }
    color([0.7,0.85,0.9,0.6]) hinge_knuckles(true);
    color("Ivory") translate([0,hinge_y,hinge_z]) rotate([0,0,90]) headed_pin(30);
}
else if(part=="saddle_assembly") saddle_assembly();
else if(part=="saddle_25") saddle_assembly(25);
else if(part=="saddle_60") saddle_assembly(60);
else if(part=="strap_route") strap_route_section();
else if(part=="strap_route_released") strap_route_section(true);
else if(part=="checks") geometry_checks();
else if(part=="closure_checks") closure_checks();
else if(part=="motion_checks") motion_checks();
else if(part=="loaded_fit_checks") loaded_fit_checks();
else if(part=="assembly") assembly();
else if(part=="exploded") assembly(20);
else if(part=="fitcheck") {
    color([0.4,0.7,0.8,0.45]) base();
    color([0.55,0.72,0.9,0.5]) tray();
    electronics();
}
else if(part=="tray_detail") {
    // Free-state cross-section through a tab, pocket and pedestal.
    color("LightSteelBlue") route_slice() translate([0,-tab_y,0]) base();
    color("SteelBlue") route_slice() translate([0,-tab_y,0]) tray();
    color([0.1,0.8,0.3,0.4]) route_slice() translate([0,-tab_y,0]) battery_reserve();
}
else if(part=="closed_section") {
    // Transverse section through the lid pads, lid closed, tray at nominal preload.
    color("LightSteelBlue") route_slice() translate([0,-(board_y+clamp_y),0]) union() { base(); lid(); }
    color("SteelBlue") route_slice() translate([0,-(board_y+clamp_y),0]) tray(tray_preload);
    color("SeaGreen") route_slice() translate([0,-(board_y+clamp_y),0]) electronics(tray_preload);
    color([0.1,0.8,0.3,0.4]) route_slice() translate([0,-(board_y+clamp_y),0]) battery_reserve();
}
else if(part=="stack_section") {
    // Longitudinal slice through the antenna centre shows its battery offset.
    color("LightSteelBlue") route_slice() rotate([0,0,90]) translate([1.8,0,0])
        union() { base(); lid(); }
    color("SteelBlue") route_slice() rotate([0,0,90]) translate([1.8,0,0]) tray();
    color("Silver") route_slice() rotate([0,0,90]) translate([1.8,0,0]) electronics();
    color([0.1,0.8,0.3,0.4]) route_slice() rotate([0,0,90]) translate([1.8,0,0]) battery_reserve();
}
else if(part=="section") intersection() { assembly(); translate([-100,-100,-1]) cube([100,200,80]); }
else assert(false,str("Unknown part: ",part));
