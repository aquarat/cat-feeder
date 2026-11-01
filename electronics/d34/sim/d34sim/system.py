"""Whole-controller SPICE system: three cards + inter-card leads + selected external devices."""
from . import ext
from .circuit import Circuit

INTER = ('LINK_PWR', 'LINK_TEC', 'LINK_12V')


def build(cards, harness, ctx, cards_in=('ctrl', 'pwr', 'tec'), exclude=(), brick=None, dps_in=None, dps_out=None,
          tec=None, thermo=None, fans=None, motor=False, onewire=None, extra_leads=(), extra=()):
    c = Circuit(cards, harness, ctx).add_cards(list(cards_in), exclude=exclude, ground='pwr')
    for lead in INTER:
        a, b = harness['leads'][lead]['a'][0], harness['leads'][lead]['b'][0]
        if a in cards_in and b in cards_in:
            c.lead(lead)
    info = {}
    if brick is not None and 'pwr' in cards_in:
        sn = ext.externals().get('inlet_snubber')
        far, cp = c.lead('BRICK', tap=bool(sn))
        c.add(*ext.brick(far, **brick))
        if sn and cp.get('tap'):
            tp = cp['tap']
            c.add(f"* off-board inlet snubber at the inlet socket ({sn['source']})",
                  f"Rsnub {tp['1']} snub_a {sn['R']}", f"Lsnub snub_a snub_b {sn['L']}", f"Csnub snub_b {tp['2']} {sn['C']}")
        info['BRICK'] = cp
    if dps_in is not None and 'pwr' in cards_in:
        far, cp = c.lead('DPS_IN')
        c.add(*ext.dps_input(far, **dps_in))
        info['DPS_IN'] = cp
    if dps_out is not None and 'tec' in cards_in:
        far, cp = c.lead('DPS_OUT')
        c.add(*ext.dps_output(far, **dps_out))
        info['DPS_OUT'] = cp
    if tec is not None and 'tec' in cards_in:
        far, cp = c.lead('TEC')
        c.add(*ext.tec_array(far, **tec))
        info['TEC'] = cp
    if thermo is not None and 'tec' in cards_in:
        far, cp = c.lead('THERMO')
        c.add(*ext.thermostats(far, **thermo))
        info['THERMO'] = cp
    if fans and 'tec' in cards_in:
        c.reg.need('Q2N3904_B')
        for name, kw in fans.items():
            far, cp = c.lead(name)
            if far:
                c.add(*ext.fan4(far, name.lower(), **kw))
            info[name] = cp
    if motor and 'pwr' in cards_in:
        far, cp = c.lead('MOTOR')
        c.add(*ext.motor(far, **(motor if isinstance(motor, dict) else {})))
    if onewire and 'pwr' in cards_in:
        for name, kw in onewire.items():
            far, cp = c.lead(name)
            if far:
                c.add(*ext.ds18b20(far, name.lower(), probes=harness['leads'][name].get('probes', 1), **kw))
            info[name] = cp
    if extra:
        c.add('* ---- what-if additions (NOT in the design; suggested-fix verification)', *extra)
    for lead in extra_leads:
        far, cp = c.lead(lead)
        info[lead] = (far, cp)
    return c, info
