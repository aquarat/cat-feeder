// Cable harness model, from cad/generated/harness_routes.scad, which
// scripts/harness.py writes from cad/harness.json and the ports echoed by
// part="harness_ports". Included by plenum.scad. Geometry study: route
// lengths are modelled, not measured on a built loom.
include <generated/harness_routes.scad>

// harness_routes: [id, colour, bundle dia, zone, [points]]; points are the
// filleted, sampled centreline, already trimmed clear of the plug faces.
module pl_cable(r) {
    d = r[2]; p = r[4];
    for(i=[0:len(p)-2]) hull() {
        translate(p[i]) sphere(d=d,$fn=10);
        translate(p[i+1]) sphere(d=d,$fn=10);
    }
}
module pl_harness(zone=undef, ids=undef) {
    for(r=harness_routes) if((is_undef(zone) || r[3]==zone) && (is_undef(ids) || len([for(i=ids) if(i==r[0]) 1])>0))
        pl_cable(r);
}
// Inline bodies (connectors, splices, barrel coupler): [name, p0, p1, dia].
module pl_inline_bodies() {
    for(b=harness_inline) hull() {
        translate(b[1]) sphere(d=b[3],$fn=16);
        translate(b[2]) sphere(d=b[3],$fn=16);
    }
}
module pl_harness_colour() {
    for(r=harness_routes) color(r[1]) pl_cable(r);
    color("Black") pl_inline_bodies();
}
module pl_harness_solids() { pl_harness(); pl_inline_bodies(); }
// Accessors: feeder.scad `use`s plenum.scad, so it cannot see these variables directly.
function pl_harness_routes() = harness_routes;
function pl_harness_inline() = harness_inline;
module pl_inline_body(b) { hull() { translate(b[1]) sphere(d=b[3],$fn=16); translate(b[2]) sphere(d=b[3],$fn=16); } }
