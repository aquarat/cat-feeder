// Current integrated shell plus a reconstructed legacy shell for diagnostics.
include <../../cad/parameters.scad>
use <../../cad/feeder.scad>
use <../../cad/internals.scad>
use <../../cad/pcb_mount.scad>
use <shell-fixture.scad>
use <../../cad/lib/sensor.scad>
$fn=120;
$pin_fit_h=1.8;
$lid_part="all";
part="checks";

module report(label) { echo(metric=label,mm3=volume()); children(); }
module fan() { translate([-60,-60,fan_z]) cube([120,120,25]); }
module fan_path() { translate([-60,-60,fan_z]) cube([120,120,lid_z+10-fan_z]); }
module sink_paths() {
    cooling_frames() translate([-20,-20,58]) cube([40,40,lid_z+10-58]);
}
module remaining_boards() {
    for(b=[[90,22,30,8],[180,25,45,15],[270,16,20,12]])
        rotate([0,0,b[0]]) translate([105-b[1]/2,-b[2]/2,29.5])
            cube([b[1],b[2],b[3]]);
}
module checks() {
    report("old board laminate / pockets") intersection() { pcb_envelope(); electronics_pockets(); }
    report("old board laminate / sink supports") intersection() { pcb_envelope(); cartridge_supports(); }
    report("old underside pins / raceways") intersection() { pcb_underside_pins(); wire_channels(); }
    report("old populated board / fixed internals") intersection() { pcb_populated_envelope(); internals(); }
    report("old populated loading path / fixed internals") intersection() { pcb_loading_path(); internals(); }
    report("old PCB shadow / low raceways") intersection() {
        translate([0,0,28]) linear_extrude(5) projection() pcb_envelope(); wire_channels();
    }
    report("connected terminal harness loading / adapted shell") intersection() {
        pcb_loading_path(harness=true); adapted_shell_fixture();
    }
    report("cradle loading / original ledge") intersection() {
        pcb_cartridge_loading_path(); legacy_shell_fixture();
        translate([-160,-160,81]) cube([320,320,3]);
    }
    report("ledge material removed for four notches") intersection() {
        legacy_shell_fixture(); pcb_shell_loading_notches();
    }
    report("assembled harness / original minus30 supports") intersection() {
        pcb_component_envelopes(); cartridge_supports();
        rotate([0,0,-30]) translate([82.9,-22.1,28]) cube([44.2,44.2,36]);
    }
    report("PCB raised to Z65 / full 40mm sinks") intersection() {
        translate([0,0,32]) pcb_populated_envelope(); sink_envelopes();
    }
    report("15deg PCB rotation / same cradle geometry") intersection() {
        rotate([0,0,15]) pcb_populated_envelope(); pcb_cartridge_bridges();
    }
    report("one cradle bearing shadow mm2 using 1mm prism") intersection() {
        linear_extrude(1) projection() pcb_cartridge_bridge_one();
        translate([85,-20,0]) cube([40,40,1]);
    }
    for(a=[-60:30:60]) report(str("old PCB loading / sink supports at ",a)) intersection() {
        pcb_loading_path(); cartridge_supports();
        rotate([0,0,a]) translate([82.9,-22.1,28]) cube([44.2,44.2,36]);
    }
    empty_check("adapted fixed internals / populated PCB") intersection() {
        pcb_adapted_internals(); pcb_populated_envelope();
    }
    empty_check("fan seats skirt and motor posts preserved") difference() {
        union() { fan_supports(); fan_inlet_skirt(); motor_posts(); }
        pcb_adapted_internals();
    }
    empty_check("ten unrelated cartridge support sets preserved") difference() {
        cartridge_supports();
        pcb_adapted_internals();
        for(a=[-30,0]) rotate([0,0,a])
            translate([82.9,-22.1,27.9]) cube([44.2,44.2,40]);
    }
    empty_check("adapted fixed internals / PCB loading") intersection() {
        pcb_adapted_internals(); pcb_loading_path();
    }
    empty_check("removable cradles / populated PCB") intersection() {
        pcb_cartridge_bridges(); pcb_populated_envelope();
    }
    empty_check("removable cradles / fixed internals") intersection() {
        pcb_cartridge_bridges(); pcb_adapted_internals();
    }
    empty_check("adapted fixed internals / fan loading") intersection() {
        pcb_adapted_internals(); fan_path();
    }
    empty_check("cradles / fan loading") intersection() { pcb_cartridge_bridges(); fan_path(); }
    empty_check("adapted supports / full sink loading") intersection() {
        union() { pcb_adapted_internals(); pcb_cartridge_bridges(); } sink_paths();
    }
    empty_check("new fixed supports / existing motor bridge") intersection() {
        pcb_adapted_internals(); motor_bridge();
    }
    empty_check("PCB and cradles / remaining three board allowances") intersection() {
        union() { pcb_populated_envelope(); pcb_cartridge_bridges(); pcb_adapted_internals(); }
        remaining_boards();
    }
    empty_check("adapted complete shell / populated PCB") intersection() {
        adapted_shell_fixture(); pcb_populated_envelope();
    }
    empty_check("adapted complete shell / PCB loading") intersection() {
        adapted_shell_fixture(); pcb_loading_path();
    }
    empty_check("adapted complete shell / cradles") intersection() {
        adapted_shell_fixture(); pcb_cartridge_bridges();
    }
    empty_check("PCB + cradles / full 40mm sinks") intersection() {
        union() { pcb_populated_envelope(); pcb_cartridge_bridges(); }
        sink_envelopes();
    }
    empty_check("PCB + cradles / deck") intersection() {
        union() { pcb_populated_envelope(); pcb_cartridge_bridges(); }
        translate([0,0,deck_z]) deck();
    }
    // A removal sweep of the cradles checks PCB, neighbouring fixed supports,
    // motor bridge and bore. Its own locating pegs are intentionally excluded.
    empty_check("cradle vertical removal / PCB") intersection() {
        translate([0,0,55]) linear_extrude(lid_z+10-55)
            projection() pcb_cartridge_bridges();
        pcb_populated_envelope();
    }
    empty_check("cradle vertical removal / motor bridge") intersection() {
        translate([0,0,55]) linear_extrude(lid_z+10-55)
            projection() pcb_cartridge_bridges();
        motor_bridge();
    }
    empty_check("continuous cradle loading / complete adapted shell") intersection() {
        pcb_cartridge_loading_path(); adapted_shell_fixture();
    }
    empty_check("continuous cradle loading / populated PCB") intersection() {
        pcb_cartridge_loading_path(); pcb_populated_envelope();
    }
    empty_check("terminal vertical driver access after cradle removal") intersection() {
        pcb_terminal_access_paths();
        union() { adapted_shell_fixture(); motor_bridge(); }
    }
    cube(1);
}
module view() {
    color("LightSteelBlue") pcb_adapted_internals();
    color("DarkGreen") pcb_envelope();
    color("Orange") pcb_component_envelopes();
    color("Gold") pcb_cartridge_bridges();
    color("DimGray",.3) sink_envelopes();
    color("SlateGray",.35) fan();
    color("SandyBrown") motor_bridge();
}
if(part=="checks") checks();
else if(part=="cradle") pcb_cartridge_bridge_print();
else if(part=="coupon") pcb_mount_coupon();
else if(part=="shell") adapted_shell_fixture();
else if(part=="view") view();
else if(part=="section") intersection() { view(); translate([75,-50,25]) cube([80,50,80]); }
else if(part=="pcb") pcb_populated_envelope();
else if(part=="local") {
    color("LightSteelBlue") pcb_supports();
    color("SteelBlue") pcb_cradle_pedestals();
    color("DarkGreen") pcb_envelope();
    color("Orange") pcb_component_envelopes();
    color("Gold") pcb_cartridge_bridges();
}
else if(part=="ledge") {
    color("LightSteelBlue") intersection() {
        adapted_shell_fixture(); translate([-160,-160,80]) cube([320,320,5]);
    }
    color("Gold") translate([0,0,28]) pcb_cartridge_bridges();
}
else if(part=="diagnostics") {
    report("loading/pocket") intersection() { pcb_loading_path(); pcb_supports(); }
    report("loading/pedestals") intersection() { pcb_loading_path(); pcb_cradle_pedestals(); }
    report("loading/old retained") intersection() {
        pcb_loading_path(); difference() { internals(); pcb_existing_features_keepout_cut(); }
    }
    report("cradle/component") intersection() { pcb_cartridge_bridges(); pcb_populated_envelope(); }
    cube(1);
}
