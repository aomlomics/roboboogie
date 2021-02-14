def get_values(*names):
    import json
    _all_values = json.loads("""{"p300mnt":"right","p20mnt":"left","mag_mod":"magnetic module gen2","num_samples":28,"sample_vol":70,"bead_vol":56,"wash_vol":180,"elute_vol":40,"final_vol":35}""")
    return [_all_values[n] for n in names]

import math

metadata = {
    'protocolName': 'PCR Clean-Up for Illumina 16S',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}

def run(protocol):
    [p300mnt, p20mnt, mag_mod, num_samples, sample_vol, bead_vol, wash_vol, elute_vol, final_vol] = get_values(  # noqa: F821
    'p300mnt', 'p20mnt', 'mag_mod', 'num_samples', 'sample_vol', 'bead_vol', 'wash_vol', 'elute_vol', 'final_vol')

    # Load labware and pipette
    magDeck = protocol.load_module(mag_mod, '10')
    magPlate = magDeck.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')

    res = protocol.load_labware('nest_12_reservoir_15ml', '7')

    end = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '1')

    tips20 = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '4')]

    all_tips = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_200ul', s).rows()[0] for s in [
                '8', '9', '5', '6', '2', '3']
                ]
    flat_tips = [tips for rack in all_tips for tips in rack]

    s20 = protocol.load_instrument('p20_single_gen2', p20mnt, tip_racks=tips20)
    m300 = protocol.load_instrument('p300_multi_gen2', p300mnt)

    # Variable declarations
    waste = protocol.load_labware('nest_1_reservoir_195ml', '11')['A1']
    num_cols = math.ceil(num_samples/8)
    tips1, tips2, tips3, tips4, tips5, tips6 = [
        flat_tips[i:i+num_cols] for i in range(0, num_cols*6, num_cols)
        ]
    magSampsCols = magPlate.rows()[0][:num_cols]
    magSampsWells = magPlate.wells()[:num_samples]
    elutes = end.rows()[0][:num_cols]
    beads = res['A1']
    etoh1 = [res['A2']]*6+[res['A3']]*6
    etoh2 = [res['A4']]*6+[res['A5']]*6
    tris = res['A6']

    m300.flow_rate.aspirate = 100
    m300.flow_rate.dispense = 100
    m300.flow_rate.blow_out = 200

    def supernatant(vol, tips, utips, rtips=False):
        m300.flow_rate.aspirate = 50
        for well, tip, utip in zip(magSampsCols, tips, utips):
            m300.pick_up_tip(tip)
            m300.aspirate(vol, well)
            m300.dispense(vol, waste)
            m300.blow_out()
            if rtips:
                m300.drop_tip(utip)
            else:
                m300.drop_tip()
        m300.flow_rate.aspirate = 100

    magDeck.disengage()

    init_vol = bead_vol + sample_vol

    # Add beads
    protocol.comment('\nADDING %s UL OF BEADS TO WELLS...' % bead_vol)
    for well, tip in zip(magSampsCols, tips1):
        m300.pick_up_tip(tip)
        m300.mix(10, bead_vol, beads)
        m300.aspirate(bead_vol, beads)
        m300.dispense(bead_vol, well)
        m300.mix(10, init_vol)
        m300.blow_out()
        m300.drop_tip()

    protocol.comment('\nINCUBATING FOR 5 MINUTES WITH MAGDECK DISENGAGED...')
    protocol.delay(minutes=5)
    
    protocol.comment('\nINCUBATING FOR 2 MINUTES WITH MAGDECK ENGAGED...')
    magDeck.engage()
    protocol.delay(minutes=2)

    protocol.comment('\nREMOVING SUPERNATANT...')
    supernatant(init_vol, tips2, tips1)
    magDeck.disengage()

    # Ethanol wash 1
    protocol.comment('\nADDING %s UL ETHANOL FOR WASH 1...' % wash_vol)
    for well, etoh, tip, utip in zip(magSampsCols, etoh1, tips3, tips2):
        m300.pick_up_tip(tip)
        m300.aspirate(wash_vol, etoh)
        m300.dispense(wash_vol, well)
        m300.drop_tip(utip)

    magDeck.engage()
    protocol.delay(seconds=30)

    protocol.comment('\nREMOVING SUPERNATANT...')
    supernatant(wash_vol, tips2, tips1, True)
    magDeck.disengage()

    # Ethanol wash 2
    protocol.comment('\nADDING %s UL ETHANOL FOR WASH 2...' % wash_vol)
    for well, etoh, tip, utip in zip(magSampsCols, etoh2, tips4, tips3):
        m300.pick_up_tip(tip)
        m300.aspirate(wash_vol, etoh)
        m300.dispense(wash_vol, well)
        m300.drop_tip(utip)

    protocol.comment('\nREMOVING SUPERNATANT AFTER ENGAGING MAGDECK AND WAITNG 30 SECONDS...')
    magDeck.engage()
    protocol.delay(seconds=30)
    supernatant(wash_vol, tips3, tips2, True)

    # Remove any excess ethanol with P20-Single/magSampsWells (changed from P20-Multi/magSampsCols)
    protocol.comment('\nREMOVING EXCESS ETHANOL WITH P20...')
    s20.transfer(20, magSampsWells, waste, new_tip='always')

    # Air dry
    protocol.comment('\nAIR DRYING FOR 10 MINUTES WITH MAGDECK DISENGAGED...')
    magDeck.disengage()
    protocol.delay(minutes=10)

    # Elute
    protocol.comment('\nADDING TRIS/WATER TO ELUTE DNA...')
    for well, tip, utip in zip(magSampsCols, tips5, tips3):
        m300.pick_up_tip(tip)
        m300.aspirate(elute_vol, tris)
        m300.dispense(elute_vol, well)
        m300.mix(10, elute_vol)
        m300.blow_out()
        m300.drop_tip(utip)

    protocol.comment('\nINCUBATING FOR 2 MINUTES WITH MAGDECK DISENGAGED...')
    protocol.delay(minutes=2)
    
    protocol.comment('\nINCUBATING FOR 2 MINUTES WITH MAGDECK ENGAGED...')
    magDeck.engage()
    protocol.delay(minutes=2)

    # Transfer to new plate
    protocol.comment('\nTRANSFERRING ELUATES TO CLEAN PCR PLATE IN SLOT 1...')
    m300.flow_rate.aspirate = 25
    for src, dest, tip, utip in zip(magSampsCols, elutes, tips6, tips4):
        m300.pick_up_tip(tip)
        m300.aspirate(final_vol, src)
        m300.dispense(final_vol, dest)
        m300.blow_out()
        m300.drop_tip(utip)

    protocol.comment('\nPROTOCOL COMPLETE!')
