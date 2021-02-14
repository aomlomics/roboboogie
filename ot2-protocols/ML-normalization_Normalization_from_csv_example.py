def get_values(*names):
    import json
    _all_values = json.loads("""{"input_csv":"source_plate_well,destination_plate_well,volume_sample_ul,volume_diluent_ul\\nA1,A1,1,9\\nA2,B1,1,9\\nA3,C1,10,0\\nB1,D1,1,9\\nB2,E1,1,9\\nB3,F1,1,9\\nC1,G1,1,9\\nC2,H1,1,9\\nC3,A2,1,9\\nD1,B2,10,0\\nD2,C2,1,9\\nD3,D2,1,9\\nE1,E2,1,9\\nE2,F2,1,9\\nE3,G2,1,9\\nF1,H2,10,0\\nF2,A3,10,0\\nF3,B3,10,0\\nG1,C3,10,0\\nG2,D3,10,0\\nG3,E3,1,9\\nH1,F3,1,9\\nH2,G3,1,9\\nH3,H3,1,9\\nA4,A4,1,9\\nB4,B4,10,0\\nC4,C4,1,9\\nD4,D4,1,9\\n","p20_type":"p20_single_gen2","p20_mount":"left","p300_type":"p300_single_gen2","p300_mount":"right","source_type":"nest_96_wellplate_100ul_pcr_full_skirt","dest_type":"nest_96_wellplate_100ul_pcr_full_skirt"}""")
    return [_all_values[n] for n in names]


# metadata
metadata = {
    'protocolName': 'Normalization from .csv',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.4'
}


def run(ctx):

    [input_csv, p20_type, p20_mount, p300_type,
     p300_mount, source_type, dest_type] = get_values(  # noqa: F821
        'input_csv', 'p20_type', 'p20_mount', 'p300_type', 'p300_mount',
        'source_type', 'dest_type')
    # [input_csv, p20_mount, p300_mount] = [
    #     "source plate well, destination plate well, volume sample (µl),\
    #     volume diluent (µl)\nA1, A1, 2, 28", 'right', 'left'
    # ]

    # labware
    source_plate = ctx.load_labware(source_type, '1', 'source plate')
    destination_plate = ctx.load_labware(dest_type, '2', 'destination plate')
    tiprack20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot, '20ul tiprack')
        for slot in ['3', '6']
    ]
    water = ctx.load_labware(
        'nest_12_reservoir_15ml', '5',
        'reservoir for water (channel 1)').wells()[0].bottom(5)
    tiprack300 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot, '200ul tiprack')
        for slot in ['8', '9']
    ]

    # pipettes
    p20 = ctx.load_instrument(p20_type, p20_mount, tip_racks=tiprack20)
    p300 = ctx.load_instrument(p300_type, p300_mount, tip_racks=tiprack300)

    # parse
    data = [
        [val.strip().upper() for val in line.split(',')]
        for line in input_csv.splitlines()[1:]
        if line and line.split(',')[0]]

    # perform normalization
    for s, d, vol_s, vol_w in data:
        if not vol_s:
            vol_s = 0
        else:
            vol_s = float(vol_s)
        if not vol_w:
            vol_w = 0
        else:
            vol_w = float(vol_w)

        s = source_plate.wells_by_name()[s]
        d = destination_plate.wells_by_name()[d]

        # move larger volume first
        if vol_s > vol_w:
            r1, r2 = s, water
            vol1, vol2 = vol_s, vol_w
            drop = True
        else:
            r1, r2 = water, s
            vol1, vol2 = vol_w, vol_s
            drop = False

        # pre-transfer diluent
        pip = p300 if vol1 > 20 else p20
        pip.pick_up_tip()
        pip.transfer(vol1, r1, d.bottom(2), new_tip='never')
        pip.blow_out(d.top(-2))
        if drop:
            pip.drop_tip()

        # transfer sample
        pip = p300 if vol2 > 20 else p20
        pipmix = p300 if (vol1 + vol2) > 20 else p20
        if vol2 != 0:
            if not pip.hw_pipette['has_tip']:
                pip.pick_up_tip()
            pip.transfer(vol2, r2, d, new_tip='never')
            pip.blow_out(d.top(-2))
            pipmix.mix(10, vol1 + vol2, d)
        for p in [p20, p300]:
            if p.hw_pipette['has_tip']:
                p.drop_tip()
