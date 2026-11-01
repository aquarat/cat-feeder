// Prototype parts plus packaging study. See README for unfinished interfaces.
use <../cad/lib/edges.scad>
use <../cad/lib/sensor.scad>
use <internals.scad>
use <pcb_mount.scad>
use <plenum.scad>
include <parameters.scad>
part = "opened";
$fn = 120;
$pin_fit_h = 1.8;  // upstream special variables are not imported by `use`
$lid_part = "all";

module disc_quarter(r, gap=split_gap) {
    intersection() {
        circle(r=r);
        translate([gap/2,gap/2]) square([r,r]);
    }
}

// Convex rounded wedge: curved outer edge, truncated (flat) inner end.
// Keeping this convex is important: edges.scad lofts use hull().
module food_outline() {
    offset(r=food_corner_r) offset(delta=-food_corner_r)
        intersection() {
            circle(r=food_outer_r);
            polygon([[0,0],[2*tray_r,-2*tray_r*tan(food_angle/2)],
                           [2*tray_r,2*tray_r*tan(food_angle/2)]]);
            translate([food_inner_x,-tray_r]) square([tray_r,2*tray_r]);
        }
}

module food_void() {
    // One ladder, including overshoot: a real 3 mm floor fillet, not just
    // rounded corners in plan. Negative top treatment chamfers the mouth.
    ladder = edge_extrude_ladder(food_depth, bottom=food_floor_r,
        top=-edge_break, bottom_style="round", top_style="chamfer");
    translate([0,0,floor_t])
        edge_loft(concat(ladder, [[food_depth+1,edge_break]])) food_outline();
}

module sector() {
    difference() {
        union() {
            difference() {
                edge_extrude(tray_h, bottom=0.3, top=edge_break)
                    offset(r=1) offset(delta=-1) disc_quarter(tray_r);
                translate([0,0,-eps]) edge_extrude(tray_h+2*eps,top=-edge_break)
                    circle(r=tray_inner_r);
            }
            // Dry inner flange: lugs transmit torque; no seam crosses a bowl.
            translate([0,0,flange_z]) edge_ring(flange_t,
                outer_top=0.4,hole_bottom=-0.3,hole_top=-0.4) {
                disc_quarter(tray_inner_r+1);
                circle(r=hub_r+fit);
            }
        }
        for(a=[15,45,75]) rotate([0,0,a]) food_void();
        rotate([0,0,45]) translate([lug_r,0,flange_z-eps])
            edge_extrude(flange_t+2*eps,bottom=-0.3,top=-0.4)
                offset(r=fit) square([8,10],center=true);
    }
}

module drive_outline(clearance=0) {
    // Axial dog/spline coupling, NOT an involute reduction gear. A wide
    // master tooth prevents replacing a loaded tray one serving out of phase.
    offset(delta=clearance) union() {
        circle(r=drive_r);
        for(i=[0:11]) rotate([0,0,i*30])
            translate([drive_r-1,0]) offset(r=0.6)
                square([drive_tooth_r-drive_r+0.4,i==0 ? 9 : 5],center=false);
    }
}

module drive() {
    difference() {
        // Taper the complete outline, preserving valleys. Chamfering separate
        // overlapping tooth solids produces float32 slivers at their roots.
        union() {
            linear_extrude(drive_h-0.6) drive_outline();
            translate([0,0,drive_h-0.6]) linear_extrude(0.6,scale=0.98) drive_outline();
            // Axial datum for the lift-off hub, independent of the deck.
            edge_extrude(drive_shoulder_h,top=0.4,bottom=0.3)
                circle(r=drive_shoulder_r);
        }
        // A blind socket seats on the measured shaft tip, leaving clearance
        // above the fixed motor face. Final shaft fit needs a physical trial.
        translate([0,0,-eps]) linear_extrude(drive_h-drive_roof+eps)
            intersection() {
                circle(d=shaft_d+0.15);
                translate([-shaft_d,-shaft_d])
                    square([shaft_d+shaft_flat_x+0.075,2*shaft_d]);
            }
    }
}

module hub() {
    difference() {
        union() {
            edge_extrude(hub_lip_t,top=0.4,bottom=0.3) circle(r=tray_inner_r-0.5);
            edge_extrude(hub_h,top=0.6) circle(r=hub_r);
            for(a=[45:90:315]) rotate([0,0,a]) translate([lug_r,0,hub_lip_t-eps])
                edge_extrude(4,top=0.6) square([8,10],center=true);
            // Two dry, support-free finger tabs, below the closed lid.
            for(x=[-39,39]) translate([x,0,hub_h-0.5])
                edge_extrude(9,top=0.8) offset(r=0.8)
                    square([2.4,10.4],center=true);
        }
        translate([0,0,-eps]) linear_extrude(hub_h+2*eps) drive_outline(fit);
    }
}

module tray_assembly() {
    rotate([0,0,15]) {
        for(a=[0:90:270]) color(a==0 ? "Wheat" : "Moccasin")
            rotate([0,0,a]) translate([0,0,tray_z]) sector();
        color("DarkOrange") translate([0,0,hub_z]) hub();
        color("DimGray") translate([0,0,drive_z]) drive();
    }
}

module cooling_frames() {
    for(a=[0:360/cooling_positions:359]) rotate([0,0,a])
        translate([cooling_radius,0,0]) children();
}

module tec_envelopes() {
    // Cold ceramic faces sit at the deck/tray datum, with no metal cap.
    cooling_frames() translate([-tec_size/2,-tec_size/2,deck_top-tec_t])
        cube([tec_size,tec_size,tec_t]);
}

module sink_envelopes() {
    cooling_frames() translate([-sink_w/2,-sink_w/2,deck_top-tec_t-sink_h])
        cube([sink_w,sink_w,sink_h]);
}

module deck() {
    if(plenum) plenum_deck(); else difference() {
        cylinder(r=deck_r,h=deck_t);
        translate([0,0,-eps]) cylinder(r=drive_bore_r+1,h=deck_t+2*eps);
        // Hub's lift flange is below the tray; it picks up the dry flanges
            // after 0.3 mm lift. Running weight rests on the deck/direct TEC faces.
        translate([0,0,deck_t-2.3]) cylinder(r=tray_inner_r+fit,h=2.3+eps);
        cooling_frames() {
            // Direct TEC-to-PETG trial; no cap recess or intermediate metal plate.
            // Hot-side contact retention and moisture details remain bench interfaces.
            translate([-(sink_w+2)/2,-(sink_w+2)/2,-eps])
                cube([sink_w+2,sink_w+2,deck_t-tec_t+eps]);
            translate([-tec_window_w/2,-tec_window_w/2,-eps])
                cube([tec_window_w,tec_window_w,deck_t+2*eps]);
            translate([-4,tec_size/2,deck_t-tec_t]) cube([4,4,tec_t+eps]);
        }
    }
}

module deck_quarter() {
    if(plenum) plenum_deck_quarter(); else direct_deck_quarter();
}

module direct_deck_quarter() {
    // Packaging coupon, flat chilled face on bed. Shell/infill is a slicer
    // choice: 0.8 mm skins, 5–8% infill. No foam pocket or bought insulation.
    translate([0,0,deck_t]) rotate([180,0,0]) intersection() {
        // Physical seams are at 15+90n degrees, between cooling cartridges.
        rotate([0,0,-15]) deck(); translate([split_gap/2,split_gap/2,-eps])
            cube([deck_r,deck_r,deck_t+2*eps]);
    }
}

module feeder_hinge(top=false) {
    // Upstream production wall y=28.5, AXIS y=32.0, z=14.1. Account for
    // its 3.5 mm outboard pivot; translating from the wall detaches the hinge.
    translate([0,hinge_y-32,hinge_z-14.1]) hinge_knuckles(top);
}

module feeder_latches() {
    rotate([0,0,clip_angle])
        translate([body_r+3,0,lid_z-1.9]) children();
}

module vent_outline(length,width) {
    offset(r=0.7) square([length-1.4,width-1.4],center=true);
}

module floor_intake_cutters() {
    // 34 slots. Top/bottom easing stays clear of the fan's corner bearing lands.
    for(x=[-28,28],i=[-8:8]) translate([x,i*intake_y_extent/8,leg_h-eps])
        edge_extrude(base_floor_t+2*eps,bottom=-0.3,top=-0.3)
            vent_outline(50,intake_slot_w);
}

module fan_inlet_coupon() {
    // Production inlet, skirt and fan seats on a small printable floor coupon.
    translate([0,0,-leg_h]) union() {
        difference() {
            translate([0,0,leg_h]) edge_extrude(base_floor_t,bottom=0.3)
                offset(r=2) square([120,120],center=true);
            floor_intake_cutters();
        }
        fan_supports();
        fan_inlet_skirt();
    }
}

module shell() {
    difference() {
        union() {
            translate([0,0,leg_h]) edge_ring(lid_z-leg_h,
                outer_bottom=1,outer_top=0.5) {
                    circle(r=body_r); circle(r=shell_inner_r);
                }
            // Enclosed underside. Honeycomb is generated by the slicer, not CAD.
            translate([0,0,leg_h]) cylinder(r=body_r-0.5,h=base_floor_t);
            // Dry ledge supports the deck, with four cradle-loading notches.
            translate([0,0,deck_z-3]) linear_extrude(3)
                difference() { circle(r=shell_inner_r+1); circle(r=deck_r-3.5); }
        }
        // Upper hot-bay exhaust band, below the solid deck ledge.
        for(a=[0:vent_pitch:359]) rotate([0,0,a])
            translate([shell_inner_r-1,0,vent_z+vent_h/2]) rotate([0,90,0])
                linear_extrude(shell_wall_t+2) vent_outline(vent_h,vent_w);
        // Long horizontal intake slits under the fan only. Board bays keep
        // solid floors; webs between the slits carry the enclosure loads.
        floor_intake_cutters();
        if(plenum) plenum_shell_cuts(); else pcb_shell_loading_notches();
    }
    feeder_hinge(false);
    feeder_latches() latch_mount();
    // Integral feet in this packaging study (no bought rubber feet).
    for(a=[45:90:315]) rotate([0,0,a]) translate([body_r-8,0,0])
        edge_extrude(leg_h+2,bottom=1,top=1) circle(r=8);
    if(plenum) plenum_internals(); else pcb_adapted_internals();
}

function clamp01(x) = max(0,min(1,x));
function smooth01(x) = let(t=clamp01(x)) t*t*(3-2*t);
function lid_top_h(x,y) =
    let(r2=(x*x+y*y)/(body_r*body_r),
        dome=lid_h+dome_rise*pow(max(0,1-r2),2),
        q=sqrt(pow(x/port_basin_rx,2)+pow((y-port_basin_y)/port_basin_ry,2)),
        blend=smooth01((q-port_basin_flat)/(1-port_basin_flat)))
    port_lip_h+(dome-port_lip_h)*blend;

module lid_blank() {
    // A smooth height-field blends a low, broad whisker basin into the dome.
    // It has a flat underside: infill can occupy its increasing thickness.
    n=180; rings=42; chamfer=0.5;
    function tid(j,i) = 1+(j-1)*n+(i%n);
    side0=1+rings*n;
    lower0=side0+n;
    bottom0=lower0+n;
    center0=bottom0+n;
    points=concat([[0,0,lid_top_h(0,0)]],
        [for(j=[1:rings],i=[0:n-1]) let(r=(body_r-chamfer)*j/rings,a=i*360/n)
            [r*cos(a),r*sin(a),lid_top_h(r*cos(a),r*sin(a))]],
        [for(i=[0:n-1]) let(a=i*360/n,r=body_r-chamfer)
            [body_r*cos(a),body_r*sin(a),lid_top_h(r*cos(a),r*sin(a))-chamfer]],
        [for(i=[0:n-1]) let(a=i*360/n) [body_r*cos(a),body_r*sin(a),chamfer]],
        [for(i=[0:n-1]) let(a=i*360/n,r=body_r-chamfer) [r*cos(a),r*sin(a),0]],
        [[0,0,0]]);
    faces=concat(
        [for(i=[0:n-1]) [0,tid(1,i),tid(1,i+1)]],
        [for(j=[1:rings-1],i=[0:n-1]) each
            [[tid(j,i),tid(j+1,i),tid(j+1,i+1)],
             [tid(j,i),tid(j+1,i+1),tid(j,i+1)]]],
        [for(i=[0:n-1]) each
            [[side0+i,side0+(i+1)%n,tid(rings,i+1)],
             [side0+i,tid(rings,i+1),tid(rings,i)]]],
        [for(start=[lower0,bottom0],i=[0:n-1]) each
            [[start+i,start+(i+1)%n,start-n+(i+1)%n],
             [start+i,start-n+(i+1)%n,start-n+i]]],
        [for(i=[0:n-1]) [center0,bottom0+(i+1)%n,bottom0+i]]);
    // OpenSCAD polyhedra use clockwise faces viewed from outside.
    translate([0,0,lid_z]) polyhedron(points=points,
        faces=[for(face=faces) [for(i=[len(face)-1:-1:0]) face[i]]],convexity=12);
}

module lid() {
    difference() {
        lid_blank();
        // Mouth is contained within ONE serving, including its edge treatment.
        rotate([0,0,270]) translate([0,0,lid_z])
            edge_loft([[-eps,0.4],[0,0.4],[0.4,0],
                [port_lip_h-0.4,0],[port_lip_h+eps,0.4+eps],
                [lid_h+dome_rise+1,0.4+eps]])
                    offset(delta=-2) food_outline();
    }
    feeder_hinge(true);
    feeder_latches() latch_catch();
}

module insulation_coupon() {
    // Plain envelope. Bambu's sparse infill and shells create the air cells.
    edge_extrude(lid_h,bottom=0.4,top=0.4) offset(r=2)
        square([56,56],center=true);
}

module lid_access_coupon() {
    translate([0,body_r,-lid_z]) intersection() {
        lid(); translate([-72,-body_r,lid_z]) cube([144,110,lid_h+dome_rise+1]);
    }
}

module moving_lid(angle) {
    translate([0,hinge_y,hinge_z]) rotate([-angle,0,0])
        translate([0,-hinge_y,-hinge_z]) lid();
}

module thermal_envelopes() {
    color("White") tec_envelopes();
    color("SlateGray") sink_envelopes();
    color("DarkSlateGray") translate([-fan_w/2,-fan_w/2,fan_z]) cube([fan_w,fan_w,fan_h]);
    // Shaft length sets the blind drive socket datum, not motor-face rubbing.
    color("Silver") translate([-21,-21,motor_face_z-motor_h]) cube([42,42,motor_h]);
    color("Gray") translate([0,0,motor_face_z]) cylinder(d=shaft_d,h=motor_shaft_l);
}

module assembly(open=false,exploded=false) {
    if(plenum) plenum_assembly(open,exploded); else direct_assembly(open,exploded);
}

module plenum_assembly(open=false,exploded=false) {
    color([0.3,0.55,0.65]) shell();
    plenum_envelopes();
    color("SandyBrown") plenum_motor_bridge();
    color("LightSteelBlue") translate([0,0,exploded?30:0]) translate([0,0,deck_z]) deck();
    translate([0,0,exploded?65:0]) tray_assembly();
    color("PowderBlue")
        if(open) moving_lid(open_angle);
        else translate([0,0,exploded?115:0]) lid();
    color("Coral") feeder_latches() clip(open?0:0.2,open?62:0);
}

module direct_assembly(open=false,exploded=false) {
    color([0.3,0.55,0.65]) shell();
    thermal_envelopes();
    color("SandyBrown") motor_bridge();
    color("SeaGreen") electronics_envelopes(include_controller=false);
    color("SeaGreen") pcb_populated_envelope();
    color("Gold") pcb_cartridge_bridges();
    color("LightSteelBlue") translate([0,0,deck_z]) deck();
    translate([0,0,exploded?65:0]) tray_assembly();
    color("PowderBlue")
        if(open) moving_lid(open_angle);
        else translate([0,0,exploded?115:0]) lid();
    color("Coral") feeder_latches() clip(open?0:0.2,open?62:0);
}

module clearance_checks() {
    if(plenum) plenum_checks(); else direct_checks();
    // Echo-only exports still need a nonempty root for standard CLI behavior.
    cube(1);
}

module pl_measure(label) { v=volume(); echo(measure=label,mm3=v); children(); }

module plenum_checks() {
    empty_check("deck / shell and internals") intersection() {
        shell(); translate([0,0,deck_z]) deck();
    }
    empty_check("deck / cold stack, hot sinks, blower, rollers") intersection() {
        translate([0,0,deck_z]) deck();
        union() { pl_cold_stack(); pl_hot_sinks(); pl_blower_env(); pl_roller_env(); }
    }
    empty_check("shell and internals / all equipment") intersection() {
        shell();
        union() { pl_hot_equipment(); pl_cold_stack(); pl_blower_env(); pl_roller_env(); }
    }
    empty_check("hot sinks / bays, fan, motor, drains") intersection() {
        pl_hot_sinks();
        union() { pl_bay_envelopes(); pl_fan_env(); pl_motor_env(); pl_drain_tubes(); }
    }
    empty_check("bays / fan, motor, drains") intersection() {
        pl_bay_envelopes(); union() { pl_fan_env(); pl_motor_env(); pl_drain_tubes(); }
    }
    empty_check("motor bridge / equipment") intersection() {
        plenum_motor_bridge();
        union() { pl_hot_equipment(); pl_cold_stack(); }
    }
    empty_check("motor bridge / shell and internals") intersection() {
        plenum_motor_bridge(); shell();
    }
    empty_check("hot-side baffles / shell and internals") intersection() {
        pl_baffles(); shell();
    }
    empty_check("hot-side baffles / equipment") intersection() {
        pl_baffles();
        union() { pl_hot_equipment(); pl_cold_stack(); pl_blower_env(); }
    }
    empty_check("hot-side baffles / motor bridge") intersection() {
        pl_baffles(); plenum_motor_bridge();
    }
    empty_check("hot-side baffles / deck") intersection() {
        pl_baffles(); translate([0,0,deck_z]) deck();
    }
    empty_check("card caps / shell, equipment, baffles, basins") intersection() {
        pl_card_caps();
        union() { shell(); pl_hot_equipment(); pl_cold_stack(); pl_baffles(); pl_basins(); }
    }
    empty_check("card caps / deck and motor bridge") intersection() {
        pl_card_caps(); union() { translate([0,0,deck_z]) deck(); plenum_motor_bridge(); }
    }
    // D34 cards: generated KiCad models with mated plugs (cad/d34_cards.scad).
    empty_check("D34 card models stay inside the 36 mm bay envelope (fallback)")
        difference() { pl_d34_installed(); pl_card_envs(); }
    empty_check("D34 cards / baffles, basins, sinks, fan, motor, bridge, DPS, drains") intersection() {
        pl_d34_installed();
        union() { pl_baffles(); pl_basins(); pl_hot_sinks(); pl_fan_env(); pl_motor_env();
                  plenum_motor_bridge(); pl_bay_envelopes(); pl_drain_tubes(); pl_cold_stack(); }
    }
    empty_check("D34 cards / devices and mounts") intersection() {
        pl_d34_installed(); union() { pl_devices(); pl_device_mounts(); pl_dps_terminals(); }
    }
    empty_check("D34 cards / deck") intersection() {
        pl_d34_installed(); translate([0,0,deck_z]) deck();
    }
    empty_check("D34 card top loading (bodies) / bridge, baffles, sinks, fan, DPS, basins, mounts")
        intersection() {
            pl_d34_cards(sweep=true);
            union() { plenum_motor_bridge(); pl_baffles(); pl_hot_sinks(); pl_fan_env();
                      pl_bay_envelopes(); pl_basins(); pl_device_mounts(); pl_devices(); pl_drain_tubes(); }
        }
    // Hand access: each plug's grip volume (12 mm on its gripped faces, swept by the
    // withdrawal travel) plus a vertical approach from above, deck and caps removed,
    // must be clear of the enclosure, baffles, sinks, devices, mounts and the other
    // cards. Crowding by the card's own parts/plugs is a layout finding reported by
    // scripts/access_order.py (build/plenum/harness/access.txt), not asserted here.
    for(c=pl_cards, k=d34_model(c[0])[4])
        empty_check(str("hand access to unplug ",c[0]," ",k[0]," (",pl_grip_mode(c[0],k[0]),") / enclosure, devices, other cards"))
        intersection() {
            pl_d34_access(c[0],k[0]);
            union() { shell(); pl_baffles(); pl_basins(); pl_hot_sinks(); pl_fan_env(); pl_motor_env();
                      plenum_motor_bridge(); pl_bay_envelopes(); pl_drain_tubes();
                      pl_devices(); pl_device_mounts(); pl_dps_terminals();
                      for(o=pl_cards) if(o[0]!=c[0]) d34_in_bay(o[0]) {
                          d34_parts(d34_model(o[0])); for(q=d34_model(o[0])[4]) d34_plug(q); } }
        }
    // Off-card devices and their tool-free mounts.
    empty_check("devices and mounts / shell and internals") intersection() {
        union() { pl_devices(); pl_device_mounts(); } shell();
    }
    empty_check("fin clips and their sensors / hot sinks (first fin gap open)") intersection() {
        union() { pl_fin_clips(); pl_fin_devices(); } pl_hot_sinks_finned();
    }
    empty_check("devices and mounts / sinks, baffles, basins, fan, motor, bridge, DPS, drains") intersection() {
        union() { pl_cold_probes(); pl_room_probe(); pl_hall_sensor(); pl_reed_body(); pl_leak_pins();
                  pl_motor_conn(); pl_panel_pod(); pl_leak_clip(); }
        union() { pl_hot_sinks(); pl_baffles(); pl_basins(); pl_fan_env(); pl_motor_env();
                  pl_bay_envelopes(); pl_drain_tubes(); pl_cold_stack(); pl_blower_env(); }
    }
    empty_check("devices (except hall sensor) / motor bridge") intersection() {
        union() { pl_fin_devices(); pl_cold_probes(); pl_room_probe(); pl_reed_body(); pl_leak_pins();
                  pl_motor_conn(); pl_panel_pod(); pl_device_mounts(); }
        plenum_motor_bridge();
    }
    empty_check("fin clips and sensors / baffles, basins, fan, bridge, DPS, drains") intersection() {
        union() { pl_fin_clips(); pl_fin_devices(); }
        union() { pl_baffles(); pl_basins(); pl_fan_env(); pl_motor_env(); plenum_motor_bridge();
                  pl_bay_envelopes(); pl_drain_tubes(); pl_cold_stack(); }
    }
    empty_check("devices and mounts / deck") intersection() {
        union() { pl_fin_devices(); pl_room_probe(); pl_hall_sensor(); pl_reed_body(); pl_leak_pins();
                  pl_motor_conn(); pl_panel_pod(); pl_device_mounts(); }
        translate([0,0,deck_z]) deck();
    }
    empty_check("chamber probes / deck (sealed bores)") intersection() {
        pl_cold_probes(); translate([0,0,deck_z]) deck();
    }
    // Cable harness (cad/harness.json via scripts/harness.py): swept bundle tubes and
    // inline connector bodies against every modelled solid. Tubes start clear of
    // their own plug/device faces. Cables may touch each other (bundled).
    empty_check("harness / shell and internals") intersection() {
        pl_harness_solids(); shell();
    }
    empty_check("harness / sinks, fan, motor, bridge, baffles, basins, drains, DPS") intersection() {
        pl_harness_solids();
        union() { pl_hot_sinks(); pl_fan_env(); pl_motor_env(); plenum_motor_bridge(); pl_baffles();
                  pl_basins(); pl_drain_tubes(); pl_bay_envelopes(); pl_tecs(); pl_spacers(); }
    }
    empty_check("harness / cold sinks, blower, rollers") intersection() {
        pl_harness_solids(); union() { pl_cold_sinks(); pl_blower_env(); pl_roller_env(); }
    }
    empty_check("harness / D34 cards and mated plugs") intersection() {
        pl_harness_solids(); pl_d34_installed();
    }
    empty_check("harness / devices, mounts, DPS terminals and card caps") intersection() {
        pl_harness_solids();
        union() { pl_devices(); pl_device_mounts(); pl_dps_terminals(); pl_card_caps(); }
    }
    empty_check("harness / deck (leads in grooves and sealed bores)") intersection() {
        pl_harness_solids(); translate([0,0,deck_z]) deck();
    }
    empty_check("harness / tray and lid (closed)") intersection() {
        pl_harness_solids(); union() { tray_assembly(); lid(); }
    }
    empty_check("inlet snubber / keeper, socket, shell wall") intersection() {
        pl_snubber(); union() { pl_inlet_keeper(); pl_kycon_body(); shell(); }
    }
    empty_check("magnet in lid / shell closed") intersection() { pl_lid_magnet(); shell(); }
    empty_check("hall sensor and post / drive at index") intersection() {
        union() { pl_hall_sensor(); plenum_motor_bridge(); }
        rotate([0,0,15]) translate([0,0,drive_z]) drive();
    }
    empty_check("evaporation basins / shell and internals") intersection() {
        pl_basins(); shell();
    }
    empty_check("evaporation basins / equipment and baffles") intersection() {
        pl_basins();
        union() { pl_hot_equipment(); pl_cold_stack(); pl_baffles(); }
    }
    empty_check("motor bridge / deck") intersection() {
        plenum_motor_bridge(); translate([0,0,deck_z]) deck();
    }
    empty_check("equipment top loading, deck removed / shell") intersection() {
        shell(); pl_loading_paths();
    }
    empty_check("motor top loading / bridge") intersection() {
        plenum_motor_bridge();
        translate([-21,-21,motor_face_z-motor_h]) cube([42,42,lid_z+10]);
    }
    empty_check("drive / deck") intersection() {
        translate([0,0,drive_z]) drive(); translate([0,0,deck_z]) deck();
    }
    empty_check("hub / deck") intersection() {
        translate([0,0,hub_z]) hub(); translate([0,0,deck_z]) deck();
    }
    empty_check("hub / tray sector") intersection() {
        translate([0,0,hub_z-tray_z]) hub(); sector();
    }
    empty_check("adjacent tray sectors") intersection() {
        sector(); rotate(90) sector();
    }
    empty_check("lid / shell closed") intersection() { lid(); shell(); }
    empty_check("closed clips / lid and shell") intersection() {
        feeder_latches() clip(0.2); union() { lid(); shell(); }
    }
    for(angle=[0:10:open_angle]) empty_check(str("opening lid at ",angle))
        intersection() {
            moving_lid(angle);
            union() { shell(); tray_assembly(); feeder_latches() clip(0,62); }
        }
    // Rollers touch the tray underside by design and are excluded here.
    for(angle=[0:5:30]) empty_check(str("rotating tray / stationary parts at ",angle))
        intersection() {
            rotate(angle) tray_assembly();
            union() { translate([0,0,deck_z]) deck(); pl_cold_sinks(); pl_blower_env();
                      shell(); lid(); pl_cold_probes(); pl_hall_sensor(); plenum_motor_bridge(); }
        }
    for(angle=[0:5:30]) empty_check(str("roller contact only at tray datum, ",angle))
        intersection() {
            rotate(angle) tray_assembly();
            translate([0,0,-0.05]) pl_roller_env();
        }
}

module direct_checks() {
    empty_check("adapted supports / installed equipment") intersection() {
        pcb_adapted_internals();
        union() { supported_equipment_envelopes(false); pcb_populated_envelope(); }
    }
    empty_check("motor bridge / installed equipment") intersection() {
        motor_bridge();
        union() { supported_equipment_envelopes(false); pcb_populated_envelope(); }
    }
    empty_check("removable PCB cradles / equipment") intersection() {
        pcb_cartridge_bridges();
        union() { supported_equipment_envelopes(false); pcb_populated_envelope(); }
    }
    empty_check("PCB cradles / complete shell") intersection() {
        pcb_cartridge_bridges(); shell();
    }
    empty_check("PCB cradles / motor bridge") intersection() {
        pcb_cartridge_bridges(); motor_bridge();
    }
    empty_check("PCB and cradles / removable deck") intersection() {
        union() { pcb_populated_envelope(); pcb_cartridge_bridges(); }
        translate([0,0,deck_z]) deck();
    }
    empty_check("unwired PCB top loading / complete shell") intersection() {
        pcb_loading_path(); shell();
    }
    empty_check("cradle top loading / complete shell") intersection() {
        pcb_cartridge_loading_path(); shell();
    }
    empty_check("cradle top loading / PCB and motor bridge") intersection() {
        pcb_cartridge_loading_path();
        union() { pcb_populated_envelope(); motor_bridge(); }
    }
    empty_check("terminal access after cartridge removal") intersection() {
        pcb_terminal_access_paths(); union() { shell(); motor_bridge(); }
    }
    empty_check("motor top loading / bridge") intersection() {
        motor_bridge();
        translate([-21,-21,motor_face_z-motor_h]) cube([42,42,lid_z+10]);
    }
    empty_check("floor-supported equipment / complete shell") intersection() {
        shell();
        union() { supported_equipment_envelopes(false); pcb_populated_envelope(); }
    }
    empty_check("motor bridge / complete shell") intersection() {
        shell(); motor_bridge();
    }
    empty_check("removable deck / shell and supports") intersection() {
        shell(); translate([0,0,deck_z]) deck();
    }
    empty_check("direct TECs and sinks / deck") intersection() {
        union() { tec_envelopes(); sink_envelopes(); }
        translate([0,0,deck_z]) deck();
    }
    empty_check("direct TECs / shell and supports") intersection() {
        tec_envelopes(); shell();
    }
    // Board/fan/cartridge passages above their final seats, with deck removed.
    empty_check("all vertical equipment paths / enclosure") intersection() {
        shell(); component_loading_paths(include_controller=false);
    }
    empty_check("remaining equipment loading / PCB and cradles") intersection() {
        component_loading_paths(include_controller=false);
        union() { pcb_populated_envelope(); pcb_cartridge_bridges(); }
    }
    empty_check("hub / tray sector") intersection() {
        translate([0,0,hub_z-tray_z]) hub(); sector();
    }
    empty_check("drive / hub") intersection() {
        translate([0,0,drive_z]) drive(); translate([0,0,hub_z]) hub();
    }
    empty_check("drive / insulation deck") intersection() {
        translate([0,0,drive_z]) drive(); translate([0,0,deck_z]) deck();
    }
    empty_check("hub / insulation deck") intersection() {
        translate([0,0,hub_z]) hub(); translate([0,0,deck_z]) deck();
    }
    empty_check("adjacent tray sectors") intersection() {
        sector(); rotate(90) sector();
    }
    empty_check("lid / shell closed") intersection() { lid(); shell(); }
    empty_check("closed clips / lid and shell") intersection() {
        feeder_latches() clip(0.2); union() { lid(); shell(); }
    }
    for(angle=[0:10:open_angle]) empty_check(str("opening lid at ",angle))
        intersection() {
            moving_lid(angle);
            union() { shell(); tray_assembly(); feeder_latches() clip(0,62); }
        }
    for(angle=[0:5:30]) empty_check(str("rotating tray / stationary parts at ",angle))
        intersection() {
            rotate(angle) tray_assembly();
            union() { translate([0,0,deck_z]) deck(); tec_envelopes(); shell(); lid(); }
        }
}

if(part=="sector") sector();
else if(part=="hub") hub();
else if(part=="drive") drive();
else if(part=="deck_quarter") deck_quarter();
else if(part=="insulation_coupon") insulation_coupon();
else if(part=="lid_access_coupon") lid_access_coupon();
else if(part=="motor_bridge") if(plenum) plenum_motor_bridge_print(); else motor_bridge_print();
else if(part=="plenum_baffle") { assert(plenum); plenum_baffle_print(); }
else if(part=="plenum_basin") { assert(plenum); plenum_basin_print(); }
else if(part=="plenum_card_cap") { assert(plenum); plenum_card_cap_print(); }
else if(part=="plenum_fin_clip") { assert(plenum); plenum_fin_clip_print(false); }
else if(part=="plenum_sensor_clip") { assert(plenum); plenum_fin_clip_print(true,0); }
else if(part=="plenum_fin_clip_90") { assert(plenum); plenum_fin_clip_print(false,90); }
else if(part=="plenum_fin_clip_66") { assert(plenum); plenum_fin_clip_print(false,66); }
else if(part=="plenum_leak_clip") { assert(plenum); plenum_leak_clip_print(); }
else if(part=="plenum_panel_pod") { assert(plenum); plenum_panel_pod_print(); }
else if(part=="plenum_inlet_keeper") { assert(plenum); plenum_inlet_keeper_print(); }
else if(part=="plenum_drive") { assert(plenum); difference() { drive(); pl_drive_magnet_pocket(); } }
else if(part=="lid" && plenum) difference() { lid(); pl_lid_magnet_pocket(); }
else if(part=="access_report" && plenum) {
    // Diagnostic (non-asserting): what blocks each plug's grip/approach volume,
    // for both grip modes, with every other plug still mated.
    for(c=pl_cards, k=d34_model(c[0])[4], mode=["pinch","ends"]) let(ref=k[0]) {
        pl_measure(str(c[0]," ",ref," ",mode," | fixed")) intersection() { pl_d34_access(c[0],ref,mode);
            union() { shell(); pl_baffles(); pl_basins(); pl_hot_sinks(); pl_fan_env(); pl_motor_env();
                      plenum_motor_bridge(); pl_bay_envelopes(); pl_drain_tubes(); } }
        pl_measure(str(c[0]," ",ref," ",mode," | devices")) intersection() { pl_d34_access(c[0],ref,mode);
            union() { pl_devices(); pl_device_mounts(); pl_dps_terminals(); } }
        pl_measure(str(c[0]," ",ref," ",mode," | card bodies")) intersection() { pl_d34_access(c[0],ref,mode); pl_d34_cards(); }
        for(o=d34_model(c[0])[4]) if(o[0]!=ref)
            pl_measure(str(c[0]," ",ref," ",mode," | plug ",o[0])) intersection() { pl_d34_access(c[0],ref,mode);
                d34_in_bay(c[0]) d34_plug(o); }
    }
    cube(1);
}
else if(part=="harness_report" && plenum) {
    // Diagnostic (non-asserting): each lead / inline body against each solid group.
    for(r=pl_harness_routes()) {
        pl_measure(str(r[0]," | shell")) intersection() { pl_cable(r); shell(); }
        pl_measure(str(r[0]," | internals")) intersection() { pl_cable(r); plenum_internals(); }
        pl_measure(str(r[0]," | sinks")) intersection() { pl_cable(r); pl_hot_sinks(); }
        pl_measure(str(r[0]," | fan")) intersection() { pl_cable(r); pl_fan_env(); }
        pl_measure(str(r[0]," | motor")) intersection() { pl_cable(r); pl_motor_env(); }
        pl_measure(str(r[0]," | bridge")) intersection() { pl_cable(r); plenum_motor_bridge(); }
        pl_measure(str(r[0]," | baffles")) intersection() { pl_cable(r); pl_baffles(); }
        pl_measure(str(r[0]," | DPS")) intersection() { pl_cable(r); pl_bay_envelopes(); }
        pl_measure(str(r[0]," | other equipment")) intersection() { pl_cable(r);
            union() { pl_basins(); pl_drain_tubes(); pl_tecs(); pl_spacers();
                      pl_cold_sinks(); pl_blower_env(); pl_roller_env(); } }
        pl_measure(str(r[0]," | cards")) intersection() { pl_cable(r); pl_d34_installed(); }
        pl_measure(str(r[0]," | devices")) intersection() { pl_cable(r);
            union() { pl_devices(); pl_device_mounts(); pl_dps_terminals(); pl_card_caps(); } }
        pl_measure(str(r[0]," | deck")) intersection() { pl_cable(r); translate([0,0,deck_z]) deck(); }
        pl_measure(str(r[0]," | tray+lid")) intersection() { pl_cable(r); union() { tray_assembly(); lid(); } }
    }
    for(b=pl_harness_inline()) {
        pl_measure(str(b[0]," | all")) intersection() {
            pl_inline_body(b);
            union() { shell(); pl_hot_sinks(); pl_fan_env(); pl_motor_env(); plenum_motor_bridge(); pl_baffles();
                      pl_basins(); pl_bay_envelopes(); pl_d34_installed(); pl_devices(); pl_device_mounts();
                      translate([0,0,deck_z]) deck(); } }
    }
    cube(1);
}
else if(part=="harness_ports") {
    for(p=concat(pl_device_ports(),pl_card_ports())) echo(port=p);
    echo(hparams=pl_harness_params());
    cube(1);
}
else if(part=="fan_inlet_coupon") fan_inlet_coupon();
else if(part=="pcb_cradle") pcb_cartridge_bridge_print();
else if(part=="pcb_mount_coupon") pcb_mount_coupon();
else if(part=="checks") clearance_checks();
else if(part=="shell") shell(); // geometry verification only; exceeds print bed
else if(part=="lid") lid();     // geometry verification only; exceeds print bed
else if(part=="clip") clip_print();
else if(part=="closure_coupon_base") closure_coupon_base();
else if(part=="closure_coupon_lid") closure_coupon_lid_print();
else if(part=="capacity") intersection() {
    food_void(); translate([-tray_r,-tray_r,0]) cube([2*tray_r,2*tray_r,tray_h]);
}
else if(part=="tray") tray_assembly();
else if(part=="access") color("PowderBlue") lid_access_coupon();
else if(part=="underside") rotate([180,0,0]) color([0.3,0.55,0.65]) shell();
else if(part=="loading" && plenum) {
    color([0.3,0.55,0.65]) intersection() {
        shell(); translate([-body_r-1,-body_r-1,0])
            cube([2*body_r+2,2*body_r+2,base_floor_top]);
    }
    color("LightSteelBlue") plenum_internals();
    color("SandyBrown") plenum_motor_bridge();
    color("SlateGray") pl_hot_sinks(); color("SeaGreen") pl_bay_envelopes();
    color("DarkSlateGray") pl_fan_env(); color("RoyalBlue") pl_drain_tubes();
    color("White") pl_tecs();
    color("Tan") pl_baffles();
    color("LightCyan") pl_basins();
    color("ForestGreen") pl_card_envs(); color("Khaki") pl_card_caps();
}
else if(part=="loading") {
    color([0.3,0.55,0.65]) intersection() {
        shell(); translate([-body_r-1,-body_r-1,0])
            cube([2*body_r+2,2*body_r+2,base_floor_top]);
    }
    color("LightSteelBlue") pcb_adapted_internals();
    color("SandyBrown") motor_bridge();
    color("SeaGreen") electronics_envelopes(include_controller=false);
    color("SeaGreen") pcb_populated_envelope();
    color("Gold") pcb_cartridge_bridges();
}
else if((part=="harness" || part=="bay_45" || part=="bay_135" || part=="bay_225" || part=="bay_315"
         || part=="harness_side") && plenum) {
    // Hot bay with the deck and caps removed: cards, devices, mounts and cables.
    a = part=="harness" || part=="harness_side" ? undef
        : part=="bay_45" ? 45 : part=="bay_135" ? 135 : part=="bay_225" ? 225 : 315;
    intersection() {
        union() {
            color([0.3,0.55,0.65]) intersection() {
                shell(); translate([-body_r-1,-body_r-1,0]) cube([2*body_r+2,2*body_r+2,deck_z]);
            }
            color("LightSteelBlue") plenum_internals();
            color("SandyBrown") plenum_motor_bridge();
            color("SlateGray") pl_hot_sinks(); color("SeaGreen") pl_bay_envelopes();
            color("DarkSlateGray") pl_fan_env(); color("Silver") pl_motor_env();
            color("RoyalBlue") pl_drain_tubes(); color("Tan") pl_baffles(); color("LightCyan") pl_basins();
            color("White") pl_tecs();
            pl_d34_colour();
            color("OrangeRed") pl_devices(); color("Wheat") pl_device_mounts(); color("DarkGray") pl_dps_terminals();
            pl_harness_colour();
        }
        if(!is_undef(a)) rotate([0,0,a-45]) translate([0,0,-1]) cube([200,200,300]);
        if(part=="harness_side") translate([-200,-200,-1]) cube([400,200,300]);
    }
}
else if(part=="cold_pocket" && plenum) {
    // Serving-site cold pocket: deck section through the site axis, sink, spacer, TEC.
    intersection() {
        union() {
            color("LightSteelBlue") translate([0,0,deck_z]) deck();
            color("LightBlue") pl_cold_sinks(); color("Silver") pl_spacers(); color("White") pl_tecs();
            color("SlateGray") pl_hot_sinks(); color("Black") pl_blower_env();
        }
        rotate([0,0,pl_serving_angle]) translate([40,-45,60]) cube([110,45,70]);
    }
}
else if(part=="plenum_deck") {
    color("LightSteelBlue") translate([0,0,deck_z]) deck();
    pl_cold_stack(); color("Black") pl_blower_env(); color("Gold") pl_roller_env();
}
else if(part=="closed") assembly();
else if(part=="opened") assembly(open=true);
else if(part=="exploded") assembly(exploded=true);
else if(part=="section") intersection() {
    assembly(); translate([-200,-200,0]) cube([400,200,250]);
}
else if(part=="insulation") intersection() {
    color("PowderBlue") lid();
    translate([0,0,lid_z-1]) cube([body_r+10,body_r+10,1+lid_h/2]);
}
else assert(false,str("Unknown part: ",part));
