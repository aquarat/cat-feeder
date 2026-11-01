// D35 cold-air plenum packaging study. Select with -D 'cooling_concept="plenum"'.
// Provisional envelopes only: no selected sinks, blower, regulator or TEC
// operating point, and no tested airflow, sealing, drainage or cooling claim.
include <parameters.scad>
use <internals.scad>
use <../cad/lib/sensor.scad>

pl_floor_z = leg_h + base_floor_t;
pl_seat_z = pl_floor_z + 1.5;
pl_bridge_z = motor_face_z - motor_h - 2;
pl_axle_z = tray_z - pl_roller_d/2;
pl_baffle_top = deck_z - 0.7;
pl_pocket_x0 = pl_cold_dr - pl_pocket[0]/2;   // site-local radial pocket edges
pl_pocket_x1 = pl_cold_dr + pl_pocket[0]/2;

module pl_sites() {
    for(a=pl_site_angles) rotate([0,0,a]) translate([pl_site_r,0,0]) children();
}
module pl_serving_site() {
    rotate([0,0,pl_serving_angle]) translate([pl_site_r,0,0]) children();
}
module pl_rollers_at() {
    for(a=pl_roller_angles) rotate([0,0,a]) translate([pl_roller_r,0,0]) children();
}
module pl_bay_frame(bay) { rotate([0,0,bay[1]]) translate([bay[2],0,0]) children(); }
module pl_baffle_frames() { for(a=pl_post_angles) rotate([0,0,a]) children(); }
module pl_post_frames() {
    for(a=pl_post_angles) rotate([0,0,a]) translate([pl_post_r,0,0]) children();
}

// ---------- Removable deck: insulation, channel walls, pockets, roller cheeks.
// Deck-local Z: 0 = underside, deck_t = channel floor (as deck()).
module pl_roller_cheeks() {
    pl_rollers_at() for(s=[-1,1]) difference() {
        translate([s>0 ? pl_roller_w/2+0.5 : -pl_roller_w/2-3.5,-8,deck_t-eps])
            cube([3,16,pl_axle_z-deck_z-deck_t+6+eps]);
        // Open-top U notch: axle and bearing drop in from above.
        translate([-10,0,pl_axle_z-deck_z]) rotate([0,90,0])
            cylinder(d=pl_axle_d+0.4,h=20,$fn=32);
        translate([-10,-(pl_axle_d+0.4)/2,pl_axle_z-deck_z]) cube([20,pl_axle_d+0.4,10]);
    }
}

module pl_site_cut(serving=false,i=0) {
    pl_tec_groove_cut(i);
    // Window: TEC and aluminium spacer pass through the full deck.
    translate([-tec_window_w/2,-tec_window_w/2,-eps])
        cube([tec_window_w,tec_window_w,deck_t+2*eps]);
    // Cold-fin pocket below the channel floor. The floor falls outward to the
    // drain; a raised collar keeps meltwater out of the TEC window. Corners are
    // clipped so the pocket stays inside the outer lip's footing.
    difference() {
        intersection() {
            hull() {
                translate([pl_pocket_x0,-pl_pocket[1]/2,pl_pocket_floor])
                    cube([eps,pl_pocket[1],deck_t-pl_pocket_floor+eps]);
                translate([pl_pocket_x1-eps,-pl_pocket[1]/2,pl_pocket_floor-pl_pocket_fall])
                    cube([eps,pl_pocket[1],deck_t-pl_pocket_floor+pl_pocket_fall+eps]);
            }
            translate([-pl_site_r,0,-1]) cylinder(r=pl_pocket_clip_r,h=deck_t+2,$fn=360);
        }
        translate([-22.5,-22.5,pl_pocket_floor-pl_pocket_fall-1])
            cube([45,45,pl_pocket_fall+1+pl_collar_h]);
    }
    // Sump slot to the drain at the low outer edge.
    translate([pl_pocket_x1-1,-4,pl_pocket_floor-pl_pocket_fall])
        cube([pl_outer_wall[0]-0.3-pl_site_r-pl_pocket_x1+1,8,
              deck_t-pl_pocket_floor+pl_pocket_fall+eps]);
    translate([pl_drain_r-pl_site_r,0,-eps]) cylinder(d=pl_drain_socket_d,h=deck_t,$fn=32);
    if(serving) {
        // Blower recess, intake well below it and an upstream intake opening.
        translate([pl_blower_x,0,0]) {
            translate([-26,pl_blower_y-26,pl_blower_bottom-deck_z-0.5])
                cube([52,52,deck_t]);
            translate([-24,pl_blower_y-24,pl_blower_well]) cube([48,48,deck_t]);
            translate([0,pl_blower_y-36,pl_blower_well]) cube([24,12,deck_t]);
            // Blower outlet discharges straight into this site's cold fins.
            translate([-12,pl_blower_y+24,pl_blower_bottom-deck_z-0.5])
                cube([24,8,deck_t]);
        }
    }
}

module plenum_deck() {
    difference() {
        union() {
            cylinder(r=deck_r,h=deck_t);
            translate([0,0,deck_t-eps]) {
                // Inner wall stops channel air reaching the drive bore.
                linear_extrude(plenum_h-1+eps) difference() {
                    circle(r=pl_inner_wall[1]); circle(r=pl_inner_wall[0]);
                }
                // Outer labyrinth lip beside the tray rim.
                linear_extrude(plenum_h+3+eps) difference() {
                    circle(r=pl_outer_wall[1]); circle(r=pl_outer_wall[0]);
                }
            }
            pl_roller_cheeks();
        }
        translate([0,0,-eps]) cylinder(r=drive_bore_r+1,h=deck_t+plenum_h+2);
        for(a=pl_site_angles) rotate([0,0,a]) translate([pl_site_r,0,0])
            pl_site_cut(a==pl_serving_angle,pl_site_i(a));
        pl_deck_cold_cuts();
        // Roller wells: the 608 rim extends below the channel floor.
        pl_rollers_at() translate([-(pl_roller_w+1)/2,-(pl_roller_d+1)/2,
                pl_axle_z-deck_z-pl_roller_d/2-0.5])
            cube([pl_roller_w+1,pl_roller_d+1,deck_t]);
    }
}

module plenum_deck_quarter() {
    // Seams on the diagonals, between sites, rollers and the blower. Prints
    // underside down: channel walls and roller cheeks rise from the top.
    intersection() {
        rotate([0,0,-pl_seam_angles[0]]) plenum_deck();
        translate([split_gap/2,split_gap/2,-eps]) cube([deck_r,deck_r,deck_t+plenum_h+5]);
    }
}

// ---------- Equipment envelopes, assembly coordinates.
module pl_hot_sinks() {
    pl_sites() translate([-pl_hot_sink[0]/2,-pl_hot_sink[1]/2,pl_hot_top-pl_hot_sink[2]])
        cube(pl_hot_sink);
}
module pl_tecs() {
    pl_sites() translate([-tec_size/2,-tec_size/2,pl_hot_top]) cube([tec_size,tec_size,pl_tec_t]);
}
module pl_spacers() {
    pl_sites() translate([-pl_spacer_w/2,-pl_spacer_w/2,pl_spacer_bottom])
        cube([pl_spacer_w,pl_spacer_w,pl_cold_bottom-pl_spacer_bottom]);
}
module pl_cold_sinks() {
    pl_sites() translate([pl_cold_dr-pl_cold_sink[0]/2,-pl_cold_sink[1]/2,pl_cold_bottom])
        cube([pl_cold_sink[0],pl_cold_sink[1],pl_cold_top-pl_cold_bottom]);
}
module pl_blower_env() {
    pl_serving_site() translate([pl_blower_x-pl_blower[0]/2,pl_blower_y-pl_blower[1]/2,pl_blower_bottom])
        cube(pl_blower);
}
module pl_roller_env() {
    pl_rollers_at() translate([0,0,pl_axle_z]) rotate([0,90,0]) {
        translate([0,0,-pl_roller_w/2]) cylinder(d=pl_roller_d,h=pl_roller_w,$fn=48);
        translate([0,0,-8]) cylinder(d=pl_axle_d,h=16,$fn=24);
    }
}
pl_tube_z0 = pl_floor_z + pl_basin_h + pl_tube_end;
module pl_drain_tubes() {
    pl_sites() translate([pl_drain_r-pl_site_r,0,pl_tube_z0])
        cylinder(d=pl_drain_d,h=deck_z+pl_drain_insert-pl_tube_z0,$fn=24);
}

// ---------- D34 vertical cards (frame: x radial along the diagonal, y tangential).
pl_card_top = pl_floor_z + pl_card[1];
pl_card_in = pl_card_x - pl_card[2];       // component-side board face
pl_cap_top = deck_z - 0.5;
pl_cap_w = pl_card[2] + 0.4 + 2*pl_cap_wall;
module pl_card_frames() { for(c=pl_cards) rotate([0,0,c[1]]) children(); }
module pl_card_boards() {
    pl_card_frames() translate([pl_card_in,-pl_card[0]/2,pl_floor_z]) cube([pl_card[2],pl_card[0],pl_card[1]]);
}
module pl_card_envs(sweep=false) {
    // Board plus component and lead envelopes between the two edge bands.
    pl_card_boards();
    z0 = pl_floor_z + pl_card_band;
    pl_card_frames() translate([pl_card_in-pl_card_depth,-pl_card[0]/2,z0])
        cube([pl_card_depth+pl_card[2]+pl_card_solder,pl_card[0],
              (sweep ? lid_z+10 : pl_card_top-pl_card_band) - z0]);
}
module pl_card_rails() {
    pl_card_frames() for(x=[pl_card_in-0.2-pl_cap_wall,pl_card_x+0.2])
        translate([x,-pl_card[0]/2+2,pl_floor_z-eps]) cube([pl_cap_wall,pl_card[0]-4,pl_card_rail_h+eps]);
}
module pl_card_posts() {
    // Shell posts beyond each card end; open-top slots take the cap's end tabs.
    pl_card_frames() for(s=[-1,1]) scale([1,s,1]) difference() {
        translate([pl_card_in-0.2-pl_cap_wall-2,pl_card[0]/2+0.3,pl_floor_z-eps])
            cube([pl_cap_w+4,4.5,pl_cap_top-pl_floor_z+eps]);
        translate([pl_card_in-0.2-pl_cap_wall-0.3,pl_card[0]/2,pl_card_top-pl_cap_engage-0.5])
            cube([pl_cap_w+0.6,2.6,50]);
    }
}
module pl_card_cap() {  // one cap, card frame
    x0 = pl_card_in-0.2-pl_cap_wall;
    translate([0,-pl_card[0]/2-2.5,0]) difference() {
        translate([x0,0,pl_card_top-pl_cap_engage]) cube([pl_cap_w,pl_card[0]+5,pl_cap_top-(pl_card_top-pl_cap_engage)]);
        translate([pl_card_in-0.2,-1,pl_card_top-pl_cap_engage-eps]) cube([pl_card[2]+0.4,pl_card[0]+7,pl_cap_engage+0.3+eps]);
    }
}
module pl_card_caps(sweep=false) {
    pl_card_frames() if(sweep) hull() { pl_card_cap(); translate([0,0,lid_z]) pl_card_cap(); }
        else pl_card_cap();
}
module plenum_card_cap_print() {  // top face on the bed, legs up
    mirror([0,0,1]) translate([-(pl_card_in-0.2-pl_cap_wall),0,-pl_cap_top]) pl_card_cap();
}
include <d34_cards.scad>
include <harness.scad>

// ---------- Evaporation basins (global frame, site at +X; rotated per site).
module pl_basin_2d() {
    a = pl_basin_half;
    // Notched round the hot-sink outer corner posts and L guides (0.6 mm clear).
    gx = pl_site_r+pl_hot_sink[0]/2+2+0.6;
    gy = [pl_hot_sink[1]/2-6.6,pl_hot_sink[1]/2+2+0.6];
    difference() {
        intersection() {
            difference() { circle(r=pl_basin_r[1],$fn=360); circle(r=pl_basin_r[0],$fn=360); }
            polygon([[0,0],[200*cos(a),-200*sin(a)],[200,0],[200*cos(a),200*sin(a)]]);
        }
        for(s=[-1,1]) scale([1,s]) translate([gx-12,gy[0]]) square([12,gy[1]-gy[0]]);
    }
    translate([pl_basin_lobe[0],-pl_basin_lobe[1]])
        square([pl_basin_r[0]+pl_basin_wall-pl_basin_lobe[0],2*pl_basin_lobe[1]]);
}
module pl_overflow_at() {
    rotate([0,0,pl_overflow[1]]) translate([pl_overflow[0],0,0]) children();
}
module pl_basin(sweep=false) {
    // Prints as modelled (underside down). The standpipe bore fits over a
    // floor stub; water above pl_overflow_h runs down the stub and out.
    top = sweep ? lid_z+10 : pl_basin_h;
    translate([0,0,pl_floor_z]) difference() {
        union() {
            difference() {
                linear_extrude(top) pl_basin_2d();
                if(!sweep) translate([0,0,pl_basin_wall])
                    linear_extrude(top) offset(delta=-pl_basin_wall) pl_basin_2d();
            }
            pl_overflow_at() cylinder(d=7.5,h=sweep ? top : pl_overflow_h,$fn=32);
        }
        pl_overflow_at() {
            translate([0,0,-eps]) cylinder(d=pl_spigot[0]+0.4,h=pl_spigot[2]+0.2,$fn=32);
            if(!sweep) cylinder(d=3.5,h=pl_basin_h+1,$fn=32);
        }
    }
}
module pl_basins(sweep=false) { for(a=pl_site_angles) rotate([0,0,a]) pl_basin(sweep); }
module plenum_basin_print() { translate([0,0,-pl_floor_z]) pl_basin(); }
module pl_bay_envelopes() {
    for(b=pl_bays) pl_bay_frame(b) translate([-b[3][0]/2,-b[3][1]/2,pl_seat_z]) cube(b[3]);
}
module pl_fan_env() {
    translate([-fan_w/2,-fan_w/2,fan_z]) cube([fan_w,fan_w,fan_h]);
}
module pl_motor_env() {
    translate([-21,-21,motor_face_z-motor_h]) cube([42,42,motor_h]);
    translate([0,0,motor_face_z]) cylinder(d=shaft_d,h=motor_shaft_l);
}
// Drop-in hot-side baffle: a flat printed plate on each diagonal, seated in floor
// rails, held down by the deck. Legs straddle the fan corner; the web clears the
// fan top; an open-top slot takes the motor-bridge arm and the bay leads.
module pl_baffle_2d(sweep=false) {  // (tangential y, z)
    hi = sweep ? lid_z+10 : pl_baffle_top;
    difference() {
        union() {
            for(s=[-1,1]) translate([s>0 ? pl_baffle_leg : -pl_baffle_end,pl_floor_z])
                square([pl_baffle_end-pl_baffle_leg,hi-pl_floor_z]);
            translate([-pl_baffle_end,pl_baffle_web_z])
                square([2*pl_baffle_end,hi-pl_baffle_web_z]);
        }
        if(!sweep) translate([-pl_baffle_slot,pl_slot_bottom])
            square([2*pl_baffle_slot,100]);
    }
}
module pl_baffle(sweep=false) {
    translate([pl_baffle_x-pl_baffle_t/2,0,0]) rotate([90,0,90])
        linear_extrude(pl_baffle_t) pl_baffle_2d(sweep);
}
module pl_baffles(sweep=false) { pl_baffle_frames() pl_baffle(sweep); }
module plenum_baffle_print() {
    linear_extrude(pl_baffle_t) translate([0,-pl_floor_z]) pl_baffle_2d();
}

module pl_cold_stack() { pl_tecs(); pl_spacers(); pl_cold_sinks(); }
module pl_hot_equipment() {
    // D34 cards are the generated KiCad models with mated plugs (cad/d34_cards.scad);
    // pl_card_envs() remains as a fallback envelope assertion in the checks.
    pl_hot_sinks(); pl_bay_envelopes(); pl_d34_installed(); pl_fan_env(); pl_motor_env(); pl_drain_tubes();
}

// ---------- Fixed floor-rooted internals (part of the shell).
module pl_hot_sink_supports() {
    z0 = pl_hot_top-pl_hot_sink[2];
    pl_sites() for(sx=[-1,1],sy=[-1,1]) scale([sx,sy,1]) {
        translate([pl_hot_sink[0]/2-4,pl_hot_sink[1]/2-4,pl_floor_z-eps])
            cube([4,4,z0-pl_floor_z+eps]);
        translate([pl_hot_sink[0]/2+0.5,pl_hot_sink[1]/2-6,pl_floor_z-eps])
            cube([1.5,6,z0+6-pl_floor_z+eps]);
        // Tangential guide legs at the outer corners only: at the inner corners the
        // baffle ends (0.5 mm off the 75 mm PR 614 faces) locate the sink tangentially.
        if(sx>0) translate([pl_hot_sink[0]/2-6,pl_hot_sink[1]/2+0.5,pl_floor_z-eps])
            cube([6,1.5,z0+6-pl_floor_z+eps]);
    }
}
module pl_motor_posts() {
    pl_post_frames() {
        translate([-2.5,-4,pl_floor_z-eps]) cube([5,8,pl_bridge_z-pl_floor_z+eps]);
        translate([-1.5,-2,pl_bridge_z-eps]) cube([3,4,3+eps]);
    }
}
module pl_bay_pockets() {
    for(b=pl_bays) pl_bay_frame(b) {
        w=b[3][0]; l=b[3][1];
        difference() {
            translate([-w/2-2,-l/2-2,pl_floor_z-eps]) cube([w+4,l+4,7+eps]);
            translate([-w/2-0.5,-l/2-0.5,pl_seat_z]) cube([w+1,l+1,10]);
            // Open-top lead exit toward the centre.
            translate([-w/2-3,-5,pl_seat_z+1]) cube([5,10,10]);
        }
    }
}
module pl_drain_collars() {
    // Overflow stubs: each basin's standpipe drops over one; bore through the floor.
    for(a=pl_site_angles) rotate([0,0,a]) pl_overflow_at()
        translate([0,0,pl_floor_z-eps]) difference() {
            cylinder(d=pl_spigot[0],h=pl_spigot[2]+eps,$fn=32);
            translate([0,0,-1]) cylinder(d=pl_spigot[1],h=pl_spigot[2]+2,$fn=32);
        }
}
module pl_baffle_rails() {
    pl_baffle_frames() for(s=[-1,1]) scale([1,s,1])
        for(x=[pl_baffle_x-pl_baffle_t/2-0.3-1.5,pl_baffle_x+pl_baffle_t/2+0.3])
            translate([x,pl_baffle_leg+1,pl_floor_z-eps])
                cube([1.5,pl_baffle_end-pl_baffle_leg-5,5+eps]);
}
module pl_sink_aprons() {
    // Closes the route under each hot sink's inner face; joins the L guides.
    z0 = pl_hot_top-pl_hot_sink[2];
    pl_sites() translate([-pl_hot_sink[0]/2-0.5-pl_apron_t,-pl_hot_sink[1]/2+6,pl_floor_z-eps])
        cube([pl_apron_t,pl_hot_sink[1]-12,z0-0.5-pl_floor_z+eps]);
}
module plenum_internals() {
    fan_supports(); fan_inlet_skirt();
    pl_hot_sink_supports(); pl_motor_posts(); pl_bay_pockets(); pl_drain_collars();
    pl_baffle_rails(); pl_sink_aprons(); pl_card_rails(); pl_card_posts();
    pl_room_boss();
}
module plenum_shell_cuts() {
    // Basin overflow outlets through the floor and one grommet for the brick lead.
    for(a=pl_site_angles) rotate([0,0,a]) pl_overflow_at() translate([0,0,leg_h-1])
        cylinder(d=pl_spigot[1],h=base_floor_t+2,$fn=32);
    // Ledge notches above each basin so it lifts straight out (deck removed).
    for(a=pl_site_angles) rotate([0,0,a]) translate([0,0,deck_z-3-eps])
        linear_extrude(3+2*eps) intersection() {
            difference() { circle(r=shell_inner_r+0.3,$fn=360); circle(r=deck_r-4,$fn=360); }
            polygon([[0,0],[300*cos(pl_basin_half+1),-300*sin(pl_basin_half+1)],[300,0],
                     [300*cos(pl_basin_half+1),300*sin(pl_basin_half+1)]]);
        }
    pl_inlet_cut();
    // Harness study: reed slot, panel pocket, their wall channels, room-probe bore.
    pl_reed_cut(); pl_panel_cut();
    translate([pl_room_xy[0],pl_room_xy[1],leg_h-1]) cylinder(d=pl_probe_smd[0]+0.3,h=base_floor_t+2,$fn=24);
    // Second exhaust slit row beside the lower half of the hot sinks.
    for(a=[0:vent_pitch:359]) if(abs(a-pl_inlet_angle) > pl_vent2_skip) rotate([0,0,a])
        translate([shell_inner_r-1,0,pl_vent2_z+vent_h/2]) rotate([0,90,0])
            linear_extrude(shell_wall_t+2)
                offset(r=0.7) square([vent_h-1.4,vent_w-1.4],center=true);
}

// ---------- Removable motor bridge, diagonal arms to the four posts.
module plenum_motor_bridge() {
    difference() {
        union() {
            translate([-23.5,-23.5,pl_bridge_z]) cube([47,47,6.8]);
            for(a=pl_post_angles) rotate([0,0,a])
                translate([20,-5,pl_bridge_z]) cube([pl_post_r+2.5-20,10,4.8]);
        }
        translate([-19,-19,pl_bridge_z-eps]) cube([38,38,8]);
        translate([-21.5,-21.5,motor_face_z-motor_h]) cube([43,43,10]);
        pl_post_frames() translate([-1.5-fit,-2-fit,pl_bridge_z-eps])
            cube([3+2*fit,4+2*fit,3+fit+eps]);
        // Stepper connector notch on the lead side.
        translate([-pl_motor_conn[0]/2-0.5,pl_motor_lead_side>0 ? 21 : -25,motor_face_z-motor_h+1])
            cube([pl_motor_conn[0]+1,4,10]);
    }
    pl_hall_post();
}
module plenum_motor_bridge_print() { translate([0,0,-pl_bridge_z]) plenum_motor_bridge(); }

module plenum_envelopes() {
    color("White") pl_tecs();
    color("Silver") pl_spacers();
    color("LightBlue") pl_cold_sinks();
    color("SlateGray") pl_hot_sinks();
    color("Black") pl_blower_env();
    color("Gold") pl_roller_env();
    color("DarkSlateGray") pl_fan_env();
    color("Silver") pl_motor_env();
    color("SeaGreen") pl_bay_envelopes();
    color("RoyalBlue") pl_drain_tubes();
    color("Tan") pl_baffles();
    color("LightCyan") pl_basins();
    pl_d34_colour();
    color("Khaki") pl_card_caps();
    color("OrangeRed") pl_devices(); color("Wheat") pl_device_mounts();
    color("DarkGray") pl_dps_terminals();
}

// Vertical sweeps: deck removed, everything below drops in from the top.
module pl_loading_paths() {
    h = lid_z+10;
    pl_sites() translate([-pl_hot_sink[0]/2,-pl_hot_sink[1]/2,pl_hot_top-pl_hot_sink[2]])
        cube([pl_hot_sink[0],pl_hot_sink[1],h]);
    for(b=pl_bays) pl_bay_frame(b) translate([-b[3][0]/2,-b[3][1]/2,pl_seat_z])
        cube([b[3][0],b[3][1],h]);
    translate([-fan_w/2,-fan_w/2,fan_z]) cube([fan_w,fan_w,h]);
    pl_baffles(sweep=true);
    pl_basins(sweep=true);
    pl_d34_cards(sweep=true);
    pl_card_caps(sweep=true);
    // Fin clips ride in with their sinks; the basin probe and room probe drop in.
    pl_fin_sweeps(h);
    hull() { pl_leak_clip(); translate([0,0,h]) pl_leak_clip(); }
    translate([pl_room_xy[0],pl_room_xy[1],pl_room_boss_top+0.1]) cylinder(d=pl_probe_smd[2],h=h,$fn=24);
}
module pl_fin_sweeps(h) {
    for(c=pl_tstats) hull() for(z=[0,h]) translate([0,0,z]) pl_clip_frame(c) {
        pl_fin_clip_local(c[3],c[4],"ksd",pl_tstat_v(c)); pl_ksd_local(c[3],c[4],pl_tstat_fd(c),pl_tstat_v(c),pl_tstat_solder(c));
        if(c[0]==pl_sink_probe[0]) { pl_sink_ds_pocket_local(c[3],c[4]); pl_sink_ds_local(c[3],c[4]); }
    }
}

// ======================================================================
// Off-card devices, tool-free mounts and cable ports (harness study,
// kb/harness.md). Port = [name, position, unit direction the lead leaves
// along]; part="harness_ports" echoes them for scripts/harness.py.
// Bodies are catalogue-class envelopes, not fitted parts.
function pl_rot(a,p) = [p[0]*cos(a)-p[1]*sin(a), p[0]*sin(a)+p[1]*cos(a), p[2]];
function pl_site_i(a) = [for(i=[0:len(pl_site_angles)-1]) if(pl_site_angles[i]==a) i][0];
function pl_unit(v) = v/norm(v);

// ---- TEC pigtails leave each module's inner edge in a deck-underside groove.
pl_tec_lead_z = pl_hot_top + 2.2;
function pl_tec_port(i) = let(a=pl_site_angles[i])
    [str("tec",a), pl_rot(a,[pl_site_r-tec_size/2-0.2,pl_tec_lead_sign[i]*pl_tec_lead_y,pl_tec_lead_z]),
     pl_rot(a,[-1,0,0])];
module pl_tec_groove_cut(i) {  // site frame, deck-local z
    w = pl_tec_groove[1];
    translate([-tec_window_w/2-pl_tec_groove[0],pl_tec_lead_sign[i]*pl_tec_lead_y-w/2,-eps])
        cube([pl_tec_groove[0]+1,w,pl_tec_groove[2]+eps]);
}

// ---- Fin clips (site frame, drawn for the +y face; mirrored for -y). A J-clip
// hooks under the outer fin's bottom edge, its inner leg rising in the first fin
// gap; its thin body holds the thermostat flange (cap side) flat on the outer fin,
// the thermostat body passing through a hole. No screws; slid up onto the fin
// before the sink drops in. Fin thickness/gap UNVERIFIED until a sink is chosen;
// thermostat envelope from pl_tstat_env (T23 sibling drawing).
pl_fin_face = pl_hot_sink[1]/2;
pl_fin_bottom = pl_hot_top-pl_hot_sink[2];
// Optional 7th element: rotation of the thermostat in the fin plane (deg). Tabs sit at
// ±pitch/2 along the rotated flange axis; both flags still point up (wires up).
function pl_tstat_v(c) = len(c)>6 ? c[6] : 0;
function pl_tenv(th) = let(e=pl_tstat_env, c=abs(cos(th)), s=abs(sin(th)))
    [e[0]*c+e[1]*s, e[0]*s+e[1]*c];                       // rotated flange bbox [x, z]
function pl_clip_depth(kind="ksd") = pl_tstat_env[2]+0.3+pl_tstat_clip[1];
function pl_clip_half(kind="ksd",th=0) = pl_tenv(th)[0]/2+0.3+pl_tstat_clip[1];
function pl_clip_top(kind,zc,th=0) = zc+pl_tenv(th)[1]/2+0.3+pl_tstat_clip[1];
module pl_fin_clip_local(xc,zc,kind="ksd",th=0) {
    t = pl_tstat_clip[1]; leg = pl_tstat_clip[2]; e = pl_tstat_env;
    F = pl_fin_face; y0 = F-pl_fin[0]-0.2-leg; d = pl_clip_depth();
    hx = pl_clip_half(kind,th); zb = pl_fin_bottom-0.3-t; zt = pl_clip_top(kind,zc,th);
    translate([xc-hx,0,0]) difference() {
        union() {
            translate([0,F+0.1,zb]) cube([2*hx,d-0.1,zt-zb]);       // body on the fin face
            translate([0,y0,zb]) cube([2*hx,F+d-y0,t]);             // hook under the fin edge
            translate([0,y0,zb]) cube([2*hx,leg,t+0.3+pl_tstat_clip[0]]); // leg in the fin gap
        }
        translate([hx,F-eps,zc]) rotate([0,-th,0])                       // flange recess
            translate([-e[0]/2-0.3,0,-e[1]/2-0.3]) cube([e[0]+0.6,e[2]+0.3+eps,e[1]+0.6]);
        translate([hx,F-eps,zc]) rotate([-90,0,0]) cylinder(d=e[3]+0.4,h=d+1,$fn=48);   // body
    }
}
function pl_tab_xz(th,s) = [s*pl_tstat_env[6]/2*cos(th), s*pl_tstat_env[6]/2*sin(th)];
// 8th element "solder": loop wires soldered to the tab ends instead of flag receptacles.
function pl_tstat_solder(c) = len(c)>7 && c[7]=="solder";
module pl_ksd_local(xc,zc,fd=1,th=0,solder=false) {  // thermostat (T23-class) + flags (fd: +1 wires up, -1 down)
    F = pl_fin_face; e = pl_tstat_env;
    translate([xc,F,zc]) rotate([0,-th,0]) translate([-e[0]/2,0,-e[1]/2]) cube([e[0],e[2],e[1]]);
    translate([xc,F+e[2],zc]) rotate([-90,0,0]) cylinder(d=e[3],h=e[4],$fn=40);
    for(s=[-1,1]) let(p=pl_tab_xz(th,s)) translate([xc+p[0],0,zc+p[1]]) {
        rotate([0,-th,0]) translate([-0.4,F+e[2]+e[4],-e[7]/2]) cube([0.8,e[5]-e[4]-e[2],e[7]]);   // tab
        if(solder) translate([-1.8,F+e[5]-4,-1.8]) cube([3.6,4.5,3.6]);    // solder joint at the tab end
        else translate([-pl_flag[0]/2,F+e[5]-pl_flag[1],fd>0 ? -e[7]/2-0.5 : e[7]/2+0.5-pl_flag[2]])
            cube([pl_flag[0],pl_flag[1]+0.5,pl_flag[2]]);
    }
}
// Hot-sink envelope with the outer fins and first gaps explicit (fin clips only).
module pl_hot_sinks_finned() {
    difference() {
        pl_hot_sinks();
        pl_sites() for(m=[0,1]) mirror([0,m,0])
            translate([-pl_hot_sink[0]/2-1,pl_fin_face-pl_fin[0]-pl_fin[1],pl_fin_bottom-1])
                cube([pl_hot_sink[0]+2,pl_fin[1],pl_hot_sink[2]-6]);
    }
}
module pl_clip_frame(c) {  // c = [name, site, face, x, z]
    rotate([0,0,c[1]]) translate([pl_site_r,0,0]) mirror([0,c[2]>0 ? 0 : 1,0]) children();
}
function pl_clip_pt(c,p) = pl_rot(c[1],[pl_site_r+p[0],c[2]*p[1],p[2]]);
// Both loop wires leave the upward flags; the port is between them.
function pl_tstat_fd(c) = len(c)>5 ? c[5] : 1;
function pl_tstat_port(c) = let(fd=pl_tstat_fd(c), dz=abs(pl_tab_xz(pl_tstat_v(c),1)[1]),
    zf = pl_tstat_solder(c) ? c[4]+fd*(dz+1.8) : c[4]+fd*(dz+pl_flag[2]-pl_tstat_env[7]/2-0.5),
    xf = pl_tstat_solder(c) ? c[3]+fd*pl_tab_xz(pl_tstat_v(c),1)[0]*sign(pl_tab_xz(pl_tstat_v(c),1)[1]) : c[3])
    [c[0], pl_clip_pt(c,[xf,pl_fin_face+pl_tstat_env[5]-(pl_tstat_solder(c) ? 2 : pl_flag[1]/2),zf]), [0,0,fd]];
// Hot-sink DS18B20: a TO-92 in a pocket on top of one KSD clip (thermal paste on
// the fin), loose leads leaving beside the thermostat's flag receptacles.
pl_to92 = [4.6,3.6,4.5];
function pl_sink_clip() = [for(c=pl_tstats) if(c[0]==pl_sink_probe[0]) c][0];
module pl_sink_ds_local(xc,zc) {
    translate([xc-pl_to92[0]/2,pl_fin_face+0.1,pl_clip_top("ksd",zc,pl_tstat_v(pl_sink_clip()))+0.4]) cube(pl_to92);
}
module pl_sink_ds_pocket_local(xc,zc) {  // added to the KSD clip that carries the sensor
    t = pl_tstat_clip[1];
    translate([xc-pl_to92[0]/2-t,pl_fin_face+0.1,pl_clip_top("ksd",zc,pl_tstat_v(pl_sink_clip()))-eps])
        difference() {
            cube([pl_to92[0]+2*t,pl_to92[1]+t,pl_to92[2]+0.4+t]);
            translate([t,-1,0.4]) cube([pl_to92[0],pl_to92[1]+1,pl_to92[2]+0.2]);
            translate([-1,-1,0.4]) cube([t+2,pl_to92[1]+1,pl_to92[2]+0.2]);   // lead exit toward the axis
        }
}
function pl_sink_probe_port(c) = let(k=pl_sink_clip())
    ["P_sink", pl_clip_pt(k,[k[3]-pl_to92[0]/2-1,pl_fin_face+pl_to92[1]/2,pl_clip_top("ksd",k[4],pl_tstat_v(k))+2.6]),
     pl_rot(k[1],[-1,0,0])];
module pl_fin_clips() {
    for(c=pl_tstats) pl_clip_frame(c) {
        pl_fin_clip_local(c[3],c[4],"ksd",pl_tstat_v(c));
        if(c[0]==pl_sink_probe[0]) pl_sink_ds_pocket_local(c[3],c[4]);
    }
}
module pl_fin_devices() {
    for(c=pl_tstats) pl_clip_frame(c) {
        pl_ksd_local(c[3],c[4],pl_tstat_fd(c),pl_tstat_v(c),pl_tstat_solder(c));
        if(c[0]==pl_sink_probe[0]) pl_sink_ds_local(c[3],c[4]);
    }
}
module plenum_fin_clip_print(sensor=false,th=0) {  // as fitted: the hook ledge on the bed
    translate([0,0,-(pl_fin_bottom-0.3-pl_tstat_clip[1])]) {
        pl_fin_clip_local(0,60,"ksd",th);
        if(sensor) pl_sink_ds_pocket_local(0,60);
    }
}

// ---- Cold-zone interfaces: sealed vertical deck bores for the blower lead and
// two DS18B20 probes. Deck-local z in pl_deck_cold_cuts.
function pl_site_pt(s,p) = pl_rot(s,[pl_site_r+p[0],p[1],p[2]]);
function pl_polar(p) = [p[1]*cos(p[0]),p[1]*sin(p[0])];
pl_probe_z0 = deck_top+pl_probe_proud-pl_probe_smd[1];   // tube bottom
pl_blower_bore_xy = pl_site_pt(pl_serving_angle,[pl_blower_bore[0],pl_blower_bore[1],0]);
module pl_deck_cold_cuts() {
    translate([pl_blower_bore_xy[0],pl_blower_bore_xy[1],-eps])
        cylinder(d=pl_blower_bore_d,h=deck_t+1,$fn=20);
    // Lead slot from the blower's outer side to the bore, 3 mm below the channel floor.
    pl_serving_site() hull() for(p=[[pl_blower_x+pl_blower[0]/2-1,pl_blower_bore[1]],pl_blower_bore])
        translate([p[0],p[1],deck_t-3]) cylinder(d=pl_blower_bore_d,h=4,$fn=20);
    for(pr=[pl_probe_food,pl_probe_chamber]) let(xy=pl_polar(pr))
        translate([xy[0],xy[1],-eps]) cylinder(d=pl_probe_smd[0]+0.3,h=deck_t+1,$fn=24);
}
module pl_cold_probes() {
    for(pr=[pl_probe_food,pl_probe_chamber]) let(xy=pl_polar(pr)) translate([xy[0],xy[1],pl_probe_z0]) {
        cylinder(d=pl_probe_smd[0],h=pl_probe_smd[1],$fn=24);
        translate([0,0,-pl_probe_smd[3]]) cylinder(d=pl_probe_smd[2],h=pl_probe_smd[3],$fn=24);
    }
}
function pl_probe_port(name,pr) = let(xy=pl_polar(pr)) [name,[xy[0],xy[1],pl_probe_z0-pl_probe_smd[3]],[0,0,-1]];
pl_blower_lead_local = [pl_blower_x+pl_blower[0]/2,pl_blower_bore[1],deck_top+3];
function pl_blower_port() = ["blower", pl_site_pt(pl_serving_angle,pl_blower_lead_local),
                             pl_rot(pl_serving_angle,[1,0,0])];

// ---- Room-air probe: through a floor boss, tip in the intake air under the floor.
pl_room_xy = [pl_probe_room[1]*cos(pl_probe_room[0]),pl_probe_room[1]*sin(pl_probe_room[0])];
pl_room_boss_top = leg_h-pl_probe_room_drop+pl_probe_smd[1];
module pl_room_boss() {
    translate([pl_room_xy[0],pl_room_xy[1],pl_floor_z-eps]) difference() {
        cylinder(d=10,h=pl_room_boss_top-pl_floor_z+eps,$fn=32);
        translate([0,0,-1]) cylinder(d=pl_probe_smd[0]+0.3,h=50,$fn=24);
    }
}
module pl_room_probe() {  // SMD-type probe: tube through the floor, boot on the boss
    translate([pl_room_xy[0],pl_room_xy[1],leg_h-pl_probe_room_drop]) {
        cylinder(d=pl_probe_smd[0],h=pl_probe_smd[1],$fn=24);
        translate([0,0,pl_probe_smd[1]]) cylinder(d=pl_probe_smd[2],h=pl_probe_smd[3],$fn=24);
    }
}
function pl_room_port() = ["P_room",[pl_room_xy[0],pl_room_xy[1],pl_room_boss_top+pl_probe_smd[3]],[0,0,1]];

// ---- Home sensor: hall switch on a post from the 45° bridge arm (part of the
// removable motor bridge), magnet in the plenum drive at the master tooth.
pl_hall_post = [34,6];           // inner radius, width
module pl_hall_post() {
    rotate([0,0,45]) translate([pl_hall_post[0],-pl_hall_post[1]/2,pl_bridge_z]) difference() {
        cube([pl_hall_r+4.5-pl_hall_post[0],pl_hall_post[1],pl_hall_top-1.6-pl_bridge_z]);
        // TO-92 seat (flat face up) and a lead groove down the +y side.
        translate([pl_hall_r-pl_hall_post[0]-2.3,0.6,pl_hall_top-1.6-pl_bridge_z-1])
            cube([4.6,4.8,2]);
        translate([pl_hall_r-pl_hall_post[0]+2,pl_hall_post[1]-1.2,6]) cube([1.8,2,60]);
    }
}
module pl_hall_sensor() {
    rotate([0,0,45]) translate([pl_hall_r-2.3,-2.4,pl_hall_top-2.6]) cube([4.6,3.6,2.6]);
}
function pl_hall_port() = ["hall", pl_rot(45,[pl_hall_r+2.9,pl_hall_post[1]/2+1.6,pl_hall_top-6]),[0,0,-1]];
// Magnet in the drive: drive frame angle so it sits over the post at tray index 0.
pl_magnet_drive_angle = 45-15;   // tray_assembly() rotates the drive by 15°
module pl_drive_magnet_pocket() {
    rotate([0,0,pl_magnet_drive_angle]) translate([pl_hall_r,0,-eps])
        cylinder(d=pl_magnet[0]+0.2,h=pl_magnet[1]+0.2,$fn=32);
}
module pl_drive_magnet() {  // drive frame
    rotate([0,0,pl_magnet_drive_angle]) translate([pl_hall_r,0,0])
        cylinder(d=pl_magnet[0],h=pl_magnet[1],$fn=32);
}

// ---- Lid reed switch and panel: rim slot / outside pocket, wall channels that
// exit under the deck ledge into the 315° bay. Shell cuts are plenum-only.
pl_ledge_exit_r = deck_r-2;
pl_chan_z = deck_z-1.85;         // horizontal leg inside the ledge
module pl_wall_channel(a,ztop) {
    rotate([0,0,a]) {
        translate([pl_wall_chan_r,0,pl_chan_z]) cylinder(d=pl_wall_chan_d,h=ztop-pl_chan_z,$fn=20);
        translate([pl_ledge_exit_r,0,pl_chan_z]) rotate([0,90,0])
            cylinder(d=pl_wall_chan_d,h=pl_wall_chan_r-pl_ledge_exit_r,$fn=20);
        translate([pl_ledge_exit_r,0,pl_chan_z-5]) cylinder(d=pl_wall_chan_d,h=5,$fn=20);
        translate([pl_wall_chan_r,0,pl_chan_z]) sphere(d=pl_wall_chan_d,$fn=20);
        translate([pl_ledge_exit_r,0,pl_chan_z]) sphere(d=pl_wall_chan_d,$fn=20);
    }
}
function pl_wall_chan_len(ztop) = (ztop-pl_chan_z)+(pl_wall_chan_r-pl_ledge_exit_r)+(pl_chan_z-deck_z+3);
module pl_reed_cut() {
    rotate([0,0,pl_reed[0]]) translate([pl_reed[1],0,lid_z-pl_reed_body[0]-0.6])
        rotate([90,0,0]) translate([0,0,-pl_reed_body[1]/2-2]) cylinder(d=pl_reed_body[0]+0.4,h=pl_reed_body[1]+4,$fn=16);
    pl_wall_channel(pl_reed[0],lid_z-1);
}
module pl_reed_body() {
    rotate([0,0,pl_reed[0]]) translate([pl_reed[1],0,lid_z-pl_reed_body[0]-0.6])
        rotate([90,0,0]) translate([0,0,-pl_reed_body[1]/2]) cylinder(d=pl_reed_body[0],h=pl_reed_body[1],$fn=16);
}
module pl_lid_magnet() {  // assembly frame, closed lid
    rotate([0,0,pl_reed[0]]) translate([pl_reed[1],0,lid_z+0.6]) cylinder(d=pl_magnet[0],h=pl_magnet[1],$fn=32);
}
module pl_lid_magnet_pocket() {
    rotate([0,0,pl_reed[0]]) translate([pl_reed[1],0,lid_z-eps]) cylinder(d=pl_magnet[0]+0.2,h=pl_magnet[1]+0.8,$fn=32);
}
function pl_reed_port() = ["reed", pl_rot(pl_reed[0],[pl_ledge_exit_r,0,deck_z-3-0.5]),[0,0,-1]];
module pl_panel_frame() { rotate([0,0,pl_panel[0]]) translate([body_r,0,pl_panel[1]]) children(); }
module pl_panel_cut() {
    pl_panel_frame() translate([-pl_panel_pocket[2],-pl_panel_pocket[0]/2,-pl_panel_pocket[1]/2])
        cube([pl_panel_pocket[2]+1,pl_panel_pocket[0],pl_panel_pocket[1]]);
    pl_wall_channel(pl_panel[0],pl_panel[1]-pl_panel_pocket[1]/2+1);
}
module pl_panel_pod_local() {  // printed pod: LED bezel + tact-switch cap, snaps into the pocket
    translate([-pl_panel_pocket[2]+0.2,-pl_panel_pocket[0]/2+0.2,-pl_panel_pocket[1]/2+0.2])
        cube([pl_panel_pocket[2]-0.2,pl_panel_pocket[0]-0.4,pl_panel_pocket[1]-0.4]);
    translate([0,0,6]) rotate([0,90,0]) cylinder(d=5.6,h=1.2,$fn=24);   // LED dome
    translate([0,0,-5]) rotate([0,90,0]) cylinder(d=9,h=1.5,$fn=32);    // button cap
}
module pl_panel_pod() { pl_panel_frame() pl_panel_pod_local(); }
module plenum_panel_pod_print() {  // back face on the bed
    translate([0,0,pl_panel_pocket[2]-0.2]) rotate([0,-90,0]) pl_panel_pod_local();
}
function pl_panel_port() = ["panel", pl_rot(pl_panel[0],[pl_ledge_exit_r,0,deck_z-3-0.5]),[0,0,-1]];

// ---- Basin-full probe: clip over basin 90's inner wall, two stainless pins.
pl_leak_r = pl_basin_r[0];
module pl_leak_clip() { rotate([0,0,pl_leak[0]]) pl_leak_clip_at0(); }
module pl_leak_clip_at0() {
    translate([0,0,pl_floor_z]) difference() {
        translate([pl_leak_r-3.4,-6,2]) cube([3.4+pl_basin_wall+2.6,12,pl_basin_h+4-2]);   // legs 4 mm over the wall
        translate([pl_leak_r-0.2,-7,-1]) cube([pl_basin_wall+0.4,14,pl_basin_h+1]);   // straddles the wall
        for(y=[-3,3]) translate([pl_leak_r+pl_basin_wall+1.3,y,0]) cylinder(d=1.6,h=20,$fn=12);
    }
}
module pl_leak_pins() {
    rotate([0,0,pl_leak[0]]) for(y=[-3,3])
        translate([pl_leak_r+pl_basin_wall+1.3,y,pl_floor_z+pl_leak[1]]) cylinder(d=1.5,h=pl_basin_h+5-pl_leak[1],$fn=12);
}
function pl_leak_port() = ["leak", pl_rot(pl_leak[0],[pl_leak_r-1.7,0,pl_floor_z+pl_basin_h+4]),[0,0,1]];
module plenum_leak_clip_print() {  // top face on the bed, open slot upward
    translate([0,0,pl_floor_z+pl_basin_h+4]) mirror([0,0,1]) rotate([0,0,-pl_leak[0]])
        translate([-pl_leak_r,0,0]) pl_leak_clip_at0();
}

// ---- DPS5005 rear terminals and comm port (inner face) [UNVERIFIED layout].
pl_dps = pl_bays[0];
function pl_dps_port(p) = [str("dps:",p[0]), pl_rot(pl_dps[1],[pl_dps[2]-pl_dps[3][0]/2,p[1],p[2]]),
                          pl_rot(pl_dps[1],[-1,0,0])];
module pl_dps_terminals() {
    for(p=pl_dps_ports) rotate([0,0,pl_dps[1]])
        translate([pl_dps[2]-pl_dps[3][0]/2-0.01,p[1]-(p[0]=="COM" ? 5 : 6),p[2]-4]) cube([0.02,p[0]=="COM" ? 10 : 12,8]);
}

// ---- Stepper lead (connector on the -y face) and fan lead (frame corner).
pl_motor_conn = [16,7,6];        // JST PH-class housing + plug on the motor side [estimate]
module pl_motor_conn() {
    translate([-pl_motor_conn[0]/2,pl_motor_lead_side>0 ? 21 : -21-pl_motor_conn[1],motor_face_z-motor_h+1])
        cube(pl_motor_conn);
}
function pl_motor_port() = ["motor",[0,pl_motor_lead_side*(21+pl_motor_conn[1]),motor_face_z-motor_h+1+pl_motor_conn[2]/2],
                            [0,pl_motor_lead_side,0]];
// The NF-A12x25 lead leaves the frame's top face inside the corner, outside the blade circle.
function pl_fan_port() = ["fan", pl_rot(pl_fan_lead_corner,[74,0,fan_z+fan_h]),[0,0,1]];

// ---- 24 V inlet: Kycon KPJX-PM-4S panel socket at 247°, flange in a shallow
// outside pocket, body through a 3 mm wall web. A printed keeper (`plenum_inlet_keeper`)
// sits in an inside counterbore; its two barbed pegs pass through the web and snap
// through the flange's screw holes, so no screw is used. Local frame: x radial.
pl_inlet_pocket = 1.2;
function pl_inlet_xo() = body_r-pl_inlet_pocket;            // flange seat (pocket floor)
function pl_inlet_xi() = pl_inlet_xo()-pl_inlet_web;        // inner face of the web
module pl_inlet_frame() { rotate([0,0,pl_inlet_angle]) translate([0,0,pl_inlet_z]) children(); }
module pl_obround(l,w,h) {  // along local y (tangential), extruded along +x
    rotate([0,90,0]) linear_extrude(h) hull() for(s=[-1,1]) translate([0,s*(l-w)/2]) circle(d=w,$fn=32);
}
module pl_inlet_cut() {
    k = pl_kycon;
    pl_inlet_frame() {
        translate([pl_inlet_xo(),0,0]) pl_obround(k[0]+0.6,k[1]+0.6,10);              // flange pocket
        translate([pl_inlet_xi()-1,0,0]) rotate([0,90,0]) cylinder(d=k[5]+0.4,h=10,$fn=40); // body hole
        for(s=[-1,1]) translate([pl_inlet_xi()-1,s*k[3]/2,0]) rotate([0,90,0]) cylinder(d=k[4]+0.3,h=10,$fn=16);
        translate([shell_inner_r-1,0,0]) pl_obround(k[0]+3,k[1]+3,pl_inlet_xi()-shell_inner_r+1); // counterbore
    }
}
module pl_kycon_body() {
    k = pl_kycon;
    pl_inlet_frame() {
        translate([pl_inlet_xo(),0,0]) pl_obround(k[0],k[1],k[2]);
        translate([pl_inlet_xo()+k[2]-k[6],0,0]) rotate([0,90,0]) cylinder(d=k[5],h=k[6]-k[2],$fn=40);
        translate([pl_inlet_xo()+k[2]-k[6]-k[7],-2.5,-2.5]) cube([k[7],5,5]);          // solder pins
    }
}
module pl_inlet_keeper_local() {  // local inlet frame
    k = pl_kycon; tk = 2;
    difference() {
        translate([pl_inlet_xi()-tk,0,0]) pl_obround(k[0]+2,k[1]+2,tk);
        translate([pl_inlet_xi()-tk-1,0,0]) rotate([0,90,0]) cylinder(d=k[5]+0.6,h=tk+2,$fn=40);
    }
    for(s=[-1,1]) translate([pl_inlet_xi()-eps,s*k[3]/2,0]) rotate([0,90,0]) difference() {
        union() {
            cylinder(d=k[4]-0.2,h=pl_inlet_web+pl_inlet_pocket+k[2]-pl_inlet_pocket+0.1+eps,$fn=16);
            translate([0,0,pl_inlet_web+k[2]+0.1]) cylinder(d1=k[4]+0.6,d2=k[4]-0.6,h=1.4,$fn=16);  // barb
        }
        translate([-0.35,-3,pl_inlet_web-1]) cube([0.7,6,6]);   // split: the barb squeezes through
    }
}
module pl_inlet_keeper() { pl_inlet_frame() pl_inlet_keeper_local(); }
// Snubber: cap on the +y side, resistor on the -y side of the socket body, both
// standing radially in the counterbore with their leads to the pins (inner end).
function pl_snub_xi() = pl_inlet_xi()-2-0.3;               // just inside the keeper plate
module pl_snubber() {
    k = pl_kycon; c = pl_snub_c; r = pl_snub_r;
    pl_inlet_frame() {
        translate([pl_snub_xi()-c[1],k[5]/2+0.6,-c[2]/2]) cube([c[1],c[0],c[2]]);
        translate([pl_snub_xi()-r[1],-(k[5]/2+0.6+r[0]/2),0]) rotate([0,90,0]) cylinder(d=r[0],h=r[1],$fn=16);
    }
}
module plenum_inlet_keeper_print() {  // plate on the bed, pegs up
    translate([0,0,0]) rotate([0,-90,0]) translate([-(pl_inlet_xi()-2),0,0]) pl_inlet_keeper_local();
}
function pl_brick_port() = ["brick",
    pl_rot(pl_inlet_angle,[pl_inlet_xo()+pl_kycon[2]-pl_kycon[6]-pl_kycon[7],0,pl_inlet_z]), pl_rot(pl_inlet_angle,[-1,0,0])];

function pl_device_ports() = concat(
    [for(i=[0:len(pl_site_angles)-1]) pl_tec_port(i)],
    [for(c=pl_tstats) pl_tstat_port(c)],
    [pl_sink_probe_port(pl_sink_probe), pl_blower_port(), pl_room_port(), pl_hall_port(),
     pl_reed_port(), pl_panel_port(), pl_leak_port(), pl_motor_port(), pl_fan_port(), pl_brick_port(),
     pl_probe_port("P_food",pl_probe_food), pl_probe_port("P_chamber",pl_probe_chamber)],
    [for(p=pl_dps_ports) pl_dps_port(p)]);
function pl_card_ports() = [for(c=pl_cards) let(m=d34_model(c[0])) for(k=m[4])
    let(p=d34_port(c[0],k[0])) [str(c[0],":",k[0]),p[0],p[1]]];

module pl_devices() {  // device bodies (assembly frame)
    pl_fin_devices(); pl_cold_probes(); pl_room_probe(); pl_hall_sensor(); pl_reed_body();
    pl_leak_pins(); pl_motor_conn(); pl_panel_pod(); pl_kycon_body(); pl_snubber();
}
module pl_device_mounts() {  // printed removable mounts not already part of shell/deck/bridge
    pl_fin_clips(); pl_leak_clip(); pl_inlet_keeper();
}

// Geometry the harness checker (scripts/harness.py) needs for its own analytic
// clearances: lengths, bends, zones and slot fill. Solids are checked here.
function pl_harness_params() = [
    ["floor_z",pl_floor_z], ["deck_z",deck_z], ["deck_top",deck_top], ["tray_z",tray_z], ["lid_z",lid_z],
    ["shell_inner_r",shell_inner_r], ["fan",[fan_z,fan_h,fan_w]], ["motor",[motor_face_z-motor_h,motor_face_z]],
    ["drive_z",drive_z], ["inner_wall",pl_inner_wall], ["site_r",pl_site_r], ["sites",pl_site_angles],
    ["hot_sink",pl_hot_sink], ["hot_top",pl_hot_top], ["cold_sink",[pl_cold_dr,pl_cold_sink[0],pl_cold_sink[1],pl_cold_bottom,pl_cold_top]],
    ["basin",[pl_basin_r[0],pl_basin_r[1],pl_basin_half,pl_basin_h]], ["drain",[pl_drain_r,pl_drain_d,pl_tube_z0]],
    ["baffle",[pl_baffle_x,pl_baffle_t,pl_baffle_slot,pl_bridge_z+4.8,pl_baffle_top,pl_baffle_end]],
    ["slot_lower",[pl_slot_bottom,pl_bridge_z]],
    ["post_angles",pl_post_angles], ["blower_bore",[pl_blower_bore_xy[0],pl_blower_bore_xy[1],pl_blower_bore_d]],
    ["probe_bores",[pl_polar(pl_probe_food),pl_polar(pl_probe_chamber)]], ["probe",pl_probe_smd],
    ["drive_bore_r",drive_bore_r+1],
    ["deck_lift",pl_deck_lift], ["inline_drop",pl_inline_drop],
    ["wall_chan",[pl_wall_chan_len(lid_z-1),pl_wall_chan_len(pl_panel[1]-pl_panel_pocket[1]/2+1)]],
    ["cards",pl_cards], ["card",[pl_card_in,pl_card_top,pl_card[0]]]
];
