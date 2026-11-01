// Millimetres. Mechanical study v0.3; direct TEC/PETG contact prototype.
// cooling_concept: "direct" = D19 direct ceramic/PETG contact (default);
// "plenum" = D35 closed-loop cold-air plenum study. Select with -D.
cooling_concept = "direct";
plenum = cooling_concept == "plenum";
portions = 12;
body_r = 158;
shell_wall_t = 12;
shell_inner_r = body_r-shell_wall_t;
tray_r = 140;
tray_inner_r = 60;
floor_t = 1.2;
food_depth = 16;
tray_h = floor_t + food_depth;
food_inner_x = 62;
food_outer_r = 137;
food_angle = 26;
food_corner_r = 5;
food_floor_r = 3;
edge_break = 0.5;
split_gap = 0.6;
fit = 0.3;                       // radial/per-side clearance, not diametral
deck_t = 18;
deck_r = shell_inner_r-0.5;      // top-loads through a constant-width shell bore
drive_bore_r = 42;
cooling_positions = 12;
cooling_radius = 105;
tec_size = 40;
tec_t = 4;
tec_window_w = tec_size+1.2;     // 0.6 mm/side for provisional seal/leads
sink_w = 40;
sink_h = 40;
leg_h = 25;
base_floor_t = 3;
base_floor_top = leg_h+base_floor_t;
fan_z = 30;                    // 2 mm intake plenum above floor; clears motor bridge
fan_w = 120;
fan_h = 25;
fan_skirt_outer = 118;
fan_skirt_inner = 114;
intake_slot_w = plenum ? 4.2 : 3.5; // plenum: +20 % fan intake area (kb/plenum-sizing.md)
intake_y_extent = 47;           // preserve corner-seat land after 0.3 mm easing
deck_z = 84;
deck_top = deck_z + deck_t;
plenum_h = 15;                  // D35 air channel between deck top and tray
tray_z = deck_top + (plenum ? plenum_h : 0);
lid_z = tray_z + tray_h + 1.2;
lid_h = 9.2;                    // retain IMU hinge/catch vertical geometry
dome_rise = 12;
port_lip_h = 1.6;               // 2.8 mm above tray rim, including running gap
port_basin_y = -102;
port_basin_rx = 65;
port_basin_ry = 92;
port_basin_flat = 0.56;
clip_angle = 315;               // one front-right clip, clear of the feeding approach
vent_w = 3;
vent_h = 22;
vent_z = 58;                    // exhaust beside exposed fins, not beneath sinks
vent_pitch = 3;                 // preserve exhaust area with 120 shorter slits
hinge_y = body_r + 3.5;
hinge_z = lid_z + 0.1;
open_angle = 110;
shaft_d = 5;                    // measure the chosen stepper before printing
shaft_flat_x = 2;               // D flat at x=2 on nominal radius 2.5
drive_r = 31;
drive_tooth_r = 36;
drive_z = tray_z - 6;
drive_h = 9;
drive_shoulder_h = 4;
drive_shoulder_r = 40.5;
drive_roof = 1;
motor_h = 28;                   // provisional short NEMA17 envelope
motor_shaft_l = 18;
motor_face_z = drive_z + drive_h - drive_roof - motor_shaft_l;
hub_z = tray_z - 2;
hub_h = 9;
hub_lip_t = 1.7;
hub_r = 42;
lug_r = 52;
flange_z = 0;                   // dry flange prints directly on the bed
flange_t = 4;
eps = 0.02;
assert(portions == 12, "Four three-portion sectors currently implemented");
assert(floor_t >= 1.2 && food_floor_r < food_depth);
assert(food_corner_r >= food_floor_r);
assert(food_outer_r + edge_break < tray_r - edge_break);
assert(food_inner_x >= tray_inner_r + 2);
assert(cooling_concept == "direct" || plenum, "Unknown cooling_concept");
assert(plenum || cooling_positions == portions);
assert(vent_z+vent_h < deck_z-3, "Exhaust must preserve the deck ledge");
assert(intake_y_extent+intake_slot_w/2+0.3 < fan_w/2-10,
    "Eased inlet cuts must preserve fan corner seats");
assert(tec_window_w/2 < (cooling_radius-tec_window_w/2)*tan(180/portions),
    "Adjacent radial TEC windows overlap");
assert(sqrt(pow(cooling_radius+tec_window_w/2,2)+pow(tec_window_w/2,2)) < deck_r);

// ---- D35 cold-air plenum study. Provisional envelopes, not selected parts. ----
// Local site frame: x radial, y tangential; airflow circulates CCW (+y).
pl_site_angles = [0,90,180,270]; // axes keep 70 mm hot sinks clear of the fan
pl_site_r = 100;
pl_serving_angle = 270;          // lid mouth; blower feeds this site first
pl_hot_sink = [70,75,45];        // Alutronic PR 614 cut to 70 mm: radial, tangential (profile width), height; fins vertical
pl_hot_top = deck_z - 0.5;       // hot base just below the deck underside
pl_spacer_w = 40;                // stock aluminium block through the deck
pl_tec_t = 4.2;                  // Adaptive ADV-127-135200-S, 40 x 40 x 4.2 mm, sealed (final D34 BOM)
pl_cold_sink = [74.5,46];        // Alutronic PR 411 (74.5 wide, radial) cut to 46 mm along flow; 3 mm base, 22 high
pl_cold_dr = 1.25;               // cold sink centre outboard of the TEC axis: 0.5 mm to the inner wall
pl_pocket = [76,64];             // cold-fin pocket below the channel floor, clipped at R140.5
pl_pocket_clip_r = 140.5;
pl_pocket_floor = deck_t - 10;   // relative to deck bottom, at the inner edge
pl_pocket_fall = 1.5;            // floor falls outward to the drain
pl_collar_h = 2;                 // keeps pocket meltwater out of the window
pl_cold_bottom = deck_z + pl_pocket_floor + pl_collar_h;
pl_cold_top = tray_z - 1;
pl_spacer_bottom = pl_hot_top + pl_tec_t;
pl_blower = [51.11,51.11,15];    // RS PRO ODB5115-12HB 5015 blower, inlet facing down
pl_blower_y = -57;               // upstream of the serving-site fins
pl_blower_x = -14;               // keeps blower corners inside the outer wall
pl_blower_bottom = tray_z - 1 - pl_blower[2];
pl_blower_well = deck_t - 8;     // intake well floor, relative to deck bottom
pl_drain_r = 138.5;              // between hot sink and shell, outside ledge
pl_drain_d = 5;                  // silicone drain tube OD
pl_drain_socket_d = 4.6;         // push-fit socket from below retains the tube
pl_drain_insert = 5;             // tube engagement in the deck
// Drop-in evaporation basins (owner, 2026-10-26): meltwater drips into a shallow
// arc in the hot exhaust behind each sink; a standpipe overflows through the floor.
pl_basin_r = [137.5,145.3];      // behind the sink corner guides, inside the bore
pl_basin_half = 25;              // degrees either side of each site
pl_basin_lobe = [135.5,12];      // inner radius, half-width: catches the tube drip
pl_basin_h = 6;
pl_basin_wall = 1.2;
pl_overflow = [141.3,20];        // radius, degrees from the site (clear of sink guides)
pl_overflow_h = 4.5;             // standpipe top above the basin underside
pl_spigot = [4.6,3,3];           // floor stub OD, bore, height
pl_tube_end = 6;                 // drip end above the basin rim
pl_roller_d = 22;                // 608 bearing as a rim roller
pl_roller_w = 7;
pl_roller_r = 131;
pl_roller_angles = [30,60,120,150,210,300,330];
pl_axle_d = 8;
pl_inner_wall = [61.5,63.5];
pl_outer_wall = [141,143.5];
pl_seam_angles = [40,130,220,310]; // deck seams, clear of sites, rollers, blower
pl_post_angles = [45,135,225,315]; // motor bridge posts, between hot sinks
pl_post_r = 89;                  // motor bridge posts on the diagonals
// name, angle, radial centre, [radial, tangential, height]
pl_bays = [  // corners stay inside the R142 deck ledge for top loading
    ["DPS5005 TEC regulator", 135, 115, [41,79,43]]
];
// D34 three-card controller (electronics/d34): vertical cards, plane tangential,
// components facing the axis. Free bay per diagonal: 44 radial x 85 x 51 (CAD-checked).
pl_cards = [["d34-ctrl",45], ["d34-pwr",225], ["d34-tec",315]];
pl_card = [81,47,1.6];           // length, height, thickness
pl_card_x = 133;                 // outer (solder-side) board face from the axis
pl_card_depth = 36;              // component side incl. mated plugs and cable bend
pl_card_solder = 2.5;            // trimmed leads
pl_card_band = 3;                // component-free band on both long edges
pl_card_rail_h = 2.5;            // floor slot rails grip the lower band only
pl_cap_engage = 2.5;             // top U-cap grips the upper band
pl_cap_wall = 1.2;
// Hot-side baffles (drop-in plates on the diagonals) force fan air through the fins.
pl_baffle_x = 78;                // plate centre plane, distance from the axis
pl_baffle_t = 2;
pl_baffle_end = 23.5;            // half-length; ends stop 0.5 mm short of the 75 mm sink side faces
pl_baffle_leg = 12;              // legs reach the floor outside |y| > leg (fan corner)
pl_baffle_web_z = fan_z + fan_h + 1;
pl_baffle_slot = 11.5;             // half-width of the open-top slot (bridge arm + harness, both sides of the post)
pl_slot_bottom = 59;             // slot floor: leads pass under the bridge arm too (fan face Z55)
pl_apron_t = 1.5;                // floor apron under each sink's inner face
pl_vent2_z = 32;                 // second exhaust slit row (plenum only)
pl_vent2_skip = 9;               // degrees kept solid either side of the inlet grommet
pl_inlet_angle = 247;            // 24 V inlet beside the pwr card's J1 end, clear of the card post
pl_inlet_z = 42;                 // and the 270 sink (harness study)
// Kycon KPJX-PM-4S 4-pin power-DIN panel socket (mates the GST160A24-R7B plug). Drawn for
// 2 x M2.5 screws; here a printed keeper's two barbed pegs pass through the wall web
// and snap through the flange holes from inside. Flange len/width/thickness, flange
// hole pitch and dia, body dia [estimate], depth behind the flange face, pin length.
pl_kycon = [25.2,14.2,1.0,19.0,2.3,12.0,9.9,4.1];
pl_inlet_web = 3;                // wall web the socket passes through (flange pocket outside)
// Reverse-brick snubber across the socket's +24 V / 0 V pins (2026-10-27): Vishay MRS25 2.2 R
// (dia, length) and a 1 uF film cap box (tangential, radial, height) [estimates; WIMA MKS2-class],
// each in a side pocket of the inlet counterbore, behind the keeper plate.
pl_snub_r = [2.5,6.5];
pl_snub_c = [4.6,7.2,9];
// ---- Off-card devices, mounts and cable interfaces (harness study 2026-10-26; kb/harness.md).
// Positions are [angle, radial x, tangential y, z] in a frame rotated by angle.
// Body sizes are catalogue-class ESTIMATES unless stated; none is a fitted part.
pl_tec_lead_y = 12;              // TEC lead exit offset along the inner edge (toward the
                                 // neighbouring junction); leads leave the TEC's inner edge
pl_tec_groove = [44,6.5,4];        // deck-underside lead groove from the window to the drive bore: length, width, depth
pl_fin = [1.4,2.2];              // PR 614 outer fin thickness and first gap [estimate from the drawing]
// Thermostat: RS PRO T24A060ASF2-15 (no published drawing) modelled on the Multicomp
// T23 sibling (oc_multicomp_t23_thermal_switch.pdf): flange length, width, thickness,
// body dia, body height below the flange, flange-to-tab-end, tab pitch, tab width.
// The clip is generated from these; re-measure on arrival and adjust.
pl_tstat_env = [30.3,21,0.4,16.1,9.6,19.28,16.2,6.35];
pl_flag = [6.6,8,16.2];            // TE 2-520129-2 flag receptacle envelope: across, along tab, flag length (wire exits +z)
// thermostat clips: name, site, face (+1 = +y), radial x on the fin, z
pl_tstats = [["T0",0,1,-8.4,56.6,1,66],["T90",90,-1,-7.4,50],["T180",180,1,-6,54.5,1,90,"solder"],["T270",270,1,-8.4,56.6,1,66]];
pl_sink_probe = ["T90"];         // hot-sink DS18B20 (TO-92) rides on this thermostat clip (bus B; lead to the 225 bay Y-splice)
pl_probe = [6.2,30,7,22];        // DS18B20 probe: tube dia, tube length, boot dia, boot length
pl_probe_smd = [5,20,5,15];      // SMD-type DS18B20 probe (BOM row: sink-base logging) [estimate]
pl_tstat_clip = [18,1.6,1.2];    // fin J-clip: inner-leg rise above the fin edge, wall, leg thickness
pl_tec_lead_sign = [-1,1,-1,1]; // per site 0/90/180/270: +1 = lead exit offset toward +y (CCW)
// Cold-zone leads cross the deck in small vertical bores sealed with a silicone bead at
// the channel floor; inline connectors hang below the deck so a quarter lifts out.
pl_blower_bore = [18,-44];       // serving-site frame [x, y]: beside the blower's outer side
pl_blower_bore_d = 4.5;          // three loose 26 AWG blower wires
pl_inline_drop = 30;             // inline connector centre below the deck underside
pl_deck_lift = 60;               // service: a quarter lifts this far before unplugging
// SMD-type DS18B20 probes stand in sealed deck bores over the central zone, tube 12 mm
// proud of the channel floor (tray underside 15 mm up); their leads drop into the hot centre.
pl_probe_food = [305,72];        // near-serving air, downstream of the serving fins (inner radius)
pl_probe_chamber = [58,70];      // channel air leaving site 0 toward the food (clear of the 45° slot lanes)
pl_probe_proud = 12;
pl_probe_room = [199.4,127.5];   // room-air probe through the floor (angle, radius); tip below the floor
pl_probe_room_drop = 10;         // SMD probe tube length below the floor underside
// Home sensor: TO-92 hall switch (DRV5023 class) on a post from the 45° motor-bridge arm,
// reading a Ø6×3 magnet in a plenum-variant drive (shoulder underside) at the master tooth.
pl_hall_r = 37;
pl_hall_top = 108;               // sensor face; drive underside is at drive_z
pl_magnet = [6,3];
// Lid switch: glass reed in a rim slot (sealed), magnet in the lid underside.
pl_reed = [286.5,152];           // angle (between exhaust slits, beyond the tec card end), radius
pl_reed_body = [2.5,14];
// Panel: snap-in pod (5 mm LED + 6×6 tact switch) in an outside wall pocket, front-right.
pl_panel = [292.5,112];          // angle (front-right, beyond the tec card end), centre height
pl_panel_pocket = [22,26,8];     // tangential, height, depth into the 12 mm wall
pl_wall_chan_d = 3.5;            // wall channel for panel/reed leads, exits under the deck ledge
pl_wall_chan_r = 151;
// Leak/basin-full probe: two stainless pins in a clip hooked over basin 90's inner wall.
pl_leak = [70,3.3];              // angle, pin-tip height above the basin underside (1.2 below overflow)
// DPS5005 rear (inner face) interfaces [UNVERIFIED layout]: name, tangential y, z.
pl_dps_ports = [["IN",19,64],["OUT",8.5,64],["COM",-24,66]];  // 4-way block OUT-,OUT+,IN-,IN+ at 5 mm [UNVERIFIED]
pl_motor_lead_side = -1;         // stepper connector faces -y (toward the 225/315 slots)
pl_fan_lead_corner = 315;        // NF-A12x25 lead leaves at this frame corner
// Grip mode per plug for the hand-access check, from scripts/access_order.py:
// "pinch" = fingers across the narrow plan dimension, "ends" = across the long one.
pl_grip_modes = [["d34-ctrl","J1","ends"],
    ["d34-ctrl","J3","ends"],
    ["d34-pwr","J4","ends"],
    ["d34-pwr","J6","ends"],
    ["d34-pwr","J9","ends"],
    ["d34-pwr","J1","ends"],
    ["d34-tec","J5","ends"],
    ["d34-tec","J3","ends"]];
assert(!plenum || pl_cold_bottom > pl_spacer_bottom, "Spacer must be positive");
assert(!plenum || pl_cold_top - pl_cold_bottom >= 15, "Cold fins too short");
assert(!plenum || pl_hot_top - pl_hot_sink[2] > base_floor_top + 5);
assert(!plenum || pl_vent2_z + vent_h < vent_z - 3, "Slit rows must keep a web");
assert(!plenum || pl_basin_r[1] < shell_inner_r - 0.5);
assert(!plenum || pl_card_rail_h < pl_card_band && pl_cap_engage < pl_card_band);
assert(!plenum || norm([pl_card_x+pl_card_solder,pl_card[0]/2]) < deck_r-4,
       "Cards must pass the deck ledge when loaded from the top");
assert(!plenum || pl_drain_r - 1.5 > pl_basin_lobe[0] + pl_basin_wall, // 3 mm tube bore
       "Tube drip must land inside the basin lobe");
assert(!plenum || pl_drain_insert < pl_pocket_floor - pl_pocket_fall - 1,
       "Drain socket must leave a floor above the tube end");
assert(!plenum || norm([pl_site_r+pl_cold_dr+pl_cold_sink[0]/2,pl_cold_sink[1]/2])
       < pl_outer_wall[0]-0.5, "Cold sink corners must clear the outer lip");
