"""Scene plan for the JANASEVA NEWS 60-second housing bulletin.

Everything the video says lives here, once, so the narration, the on-screen copy,
the subtitles and the QA checklist can be diffed against each other.

Facts are limited to the verified brief:

  * 3 lakh houses sanctioned to Andhra Pradesh under PMAY-Gramin, ~Rs 3,600 crore.
  * The event was held at Burripalem, Tenali constituency, Guntur district.
  * Union Minister Shivraj Singh Chouhan and CM Nara Chandrababu Naidu attended.
  * Roughly 76,000 houses were originally indicated; the Chief Minister's request
    for additional houses raised the number to 3 lakh.
  * The Chief Minister asked for a further 6 lakh houses.
  * A future 3 lakh more may be sanctioned after the current 3 lakh are built.
  * A 177-house 3D concrete printing pilot at Burripalem and Obulanayudupalem,
    budgeted at about Rs 14 crore, with a target of about 6 months.
  * 5.50 lakh houses handed over in the last two years and a 4.20 lakh target by
    next March, per the state government / reports.

Nothing else is claimed. In particular the video never states that 9 lakh houses
are already sanctioned: the current 3 lakh and any future allocation are kept in
separate, differently styled blocks.
"""

# Timing ---------------------------------------------------------------------
# Measured durations of assets/vo1..vo8.mp3 and the tempo used to compress them
# into a 60-second slot. make_video.py re-measures the files and asserts these
# still match, so the plan cannot silently drift from the audio.
VO_SECONDS = [6.48, 5.76, 8.64, 12.00, 10.88, 6.04, 8.56, 6.12]   # source files
TEMPO = 1.10
FPS = 30
TOTAL_FRAMES = 1800          # 60.00 s exactly at 30 fps

# Scene frame counts derived from the narration, rounded so they sum to 1800.
SCHEDULE = [179, 159, 239, 332, 301, 167, 237, 186]
assert sum(SCHEDULE) == TOTAL_FRAMES

VO_IDS = ['vo1', 'vo2', 'vo3', 'vo4', 'vo5', 'vo6', 'vo7', 'vo8']

VO_TEXT = {
    'vo1': 'ఏపీకి మూడు లక్షల పక్కా ఇళ్లు.. ఇందుకోసం మూడు వేల ఆరు వందల కోట్ల రూపాయల నిధులు!',
    'vo2': 'ప్రధానమంత్రి ఆవాస్ యోజన గ్రామీణ్ కింద ఈ ఇళ్లను ఏపీకి మంజూరు చేశారు.',
    'vo3': ('గుంటూరు జిల్లా బుర్రిపాలెంలో జరిగిన కార్యక్రమంలో కేంద్ర మంత్రి శివరాజ్ సింగ్ చౌహాన్, '
            'ముఖ్యమంత్రి చంద్రబాబు నాయుడు పాల్గొన్నారు.'),
    'vo4': ('మొదట సుమారు డెబ్బై ఆరు వేల ఇళ్ల అర్హతను సూచించగా.. అదనపు ఇళ్ల కోసం రాష్ట్ర ప్రభుత్వం '
            'చేసిన అభ్యర్థనతో.. సంఖ్యను మూడు లక్షలకు పెంచినట్లు కేంద్ర మంత్రి తెలిపారు.'),
    'vo5': ('ఇదే కార్యక్రమంలో త్రీడీ కాంక్రీట్ ప్రింటింగ్ టెక్నాలజీతో నూట డెబ్బై ఏడు ఇళ్ల పైలట్ '
            'ప్రాజెక్ట్ ప్రారంభించారు. దీని అంచనా వ్యయం పద్నాలుగు కోట్ల రూపాయలు.'),
    'vo6': 'ఈ నూట డెబ్బై ఏడు ఇళ్లను సుమారు ఆరు నెలల్లో పూర్తి చేయాలని లక్ష్యంగా పెట్టుకున్నారు.',
    'vo7': ('ప్రస్తుత మూడు లక్షల ఇళ్ల నిర్మాణం పూర్తయిన తర్వాత, మరో మూడు లక్షల ఇళ్లను మంజూరు '
            'చేసే అవకాశం ఉందని కేంద్ర మంత్రి తెలిపారు.'),
    'vo8': 'ఏపీ తాజా వార్తల కోసం జనసేవ న్యూస్ ఫాలో అవ్వండి. మీ అభిప్రాయాన్ని కామెంట్ చేయండి.',
}

# Subtitles ----------------------------------------------------------------
# Each cue carries a weight; the exact on-screen window is snapped to the real
# pauses detected in the narration (see make_video.py), so the subtitles stay
# locked to the voice instead of drifting on an estimate.
# 'hi' lists the substrings inside the cue that should render in the highlight
# colour (numbers and figures the brief asks to emphasise).
SUBS = [
    [   # 1 -- hook
        ('ఏపీకి మూడు లక్షల పక్కా ఇళ్లు', 1.0, ['మూడు లక్షల పక్కా ఇళ్లు']),
        ('ఇందుకోసం ₹3,600 కోట్లు', 1.0, ['₹3,600 కోట్లు']),
    ],
    [   # 2 -- scheme
        ('పీఎం ఆవాస్ యోజన–గ్రామీణ్ కింద', 1.0, ['ఆవాస్ యోజన–గ్రామీణ్']),
        ('ఏపీకి 3 లక్షల ఇళ్లు మంజూరు', 1.0, ['3 లక్షల ఇళ్లు']),
    ],
    [   # 3 -- event
        ('గుంటూరు జిల్లా బుర్రిపాలెంలో', 1.0, ['బుర్రిపాలెం']),
        ('కేంద్ర మంత్రి శివరాజ్ చౌహాన్', 1.0, ['కేంద్ర మంత్రి']),
        ('సీఎం చంద్రబాబు నాయుడు పాల్గొన్నారు', 1.0, ['చంద్రబాబు నాయుడు']),
    ],
    [   # 4 -- the 76,000 to 3 lakh rise
        ('మొదట సుమారు 76 వేల ఇళ్ల అర్హత', 1.0, ['76 వేల']),
        ('అదనపు ఇళ్ల కోసం రాష్ట్ర అభ్యర్థన', 1.1, []),
        ('సంఖ్యను 3 లక్షలకు పెంచినట్లు', 1.0, ['3 లక్షలకు']),
        ('కేంద్ర మంత్రి తెలిపారు', 0.9, []),
    ],
    [   # 5 -- 3D printing
        ('3D కాంక్రీట్ ప్రింటింగ్‌తో', 1.2, ['3D కాంక్రీట్']),
        ('177 ఇళ్ల పైలట్ ప్రాజెక్ట్', 1.0, ['177 ఇళ్ల']),
        ('అంచనా వ్యయం ₹14 కోట్లు', 1.0, ['₹14 కోట్లు']),
    ],
    [   # 6 -- six-month target
        ('ఈ 177 ఇళ్లను', 0.8, ['177 ఇళ్లు']),
        ('సుమారు 6 నెలల్లో పూర్తి లక్ష్యం', 1.3, ['6 నెలల్లో']),
    ],
    [   # 7 -- present vs future
        ('ప్రస్తుత 3 లక్షల ఇళ్లు పూర్తయ్యాక', 1.1, ['3 లక్షల']),
        ('మరో 3 లక్షలకు అవకాశం', 1.2, ['మరో 3 లక్షలకు']),
    ],
    [   # 8 -- CTA
        ('ఏపీ తాజా వార్తల కోసం', 0.9, []),
        ('జనసేవ న్యూస్ ఫాలో అవ్వండి', 1.0, ['జనసేవ న్యూస్']),
    ],
]

# On-screen copy --------------------------------------------------------------
BRAND = 'జనసేవ న్యూస్'
PAYOFF = 'నిజమైన సమాచారం • ప్రజల కోసం వార్తలు'
AI_LABEL = 'ఏఐతో రూపొందించిన దృశ్యం'

SCENES = [
    dict(
        key='hook', label='ప్రధాన వార్త', visual='map_overview',
        head=[('ఏపీకి 3 లక్షల ఇళ్లు!', False, 84), ('₹3,600 కోట్లు', True, 100)],
        chip='పక్కా ఇళ్లు • PMAY-గ్రామీణ్',
        footnote='ప్రధానమంత్రి ఆవాస్ యోజన–గ్రామీణ్ కింద ఏపీకి మంజూరు',
    ),
    dict(
        key='place', label='కార్యక్రమ ప్రదేశం', visual='map_zoom',
        head=[('గుంటూరు జిల్లా', False, 78), ('తెనాలి • బుర్రిపాలెం', True, 86)],
        chip='నియోజకవర్గం • తెనాలి',
        footnote='కార్యక్రమం జరిగిన గ్రామం బుర్రిపాలెం',
    ),
    dict(
        key='event', label='కార్యక్రమం', visual='photo',
        image='event_venue.jpg',
        head=[('శివరాజ్ సింగ్ చౌహాన్', False, 78), ('చంద్రబాబు నాయుడు', True, 84)],
        chip='కేంద్ర మంత్రి • ముఖ్యమంత్రి',
        footnote='కార్యక్రమ వేదిక — ఏఐ చిత్రణ, నిజ ఫోటో కాదు',
    ),
    dict(
        key='numbers', label='సంఖ్య పెంపు', visual='counter',
        head=[('76 వేల నుంచి', False, 84), ('3 లక్షలకు', True, 100)],
        chip='అర్హత → మంజూరు',
        footnote='అదనపు ఇళ్ల కోసం రాష్ట్ర ప్రభుత్వ అభ్యర్థనతో పెంపు',
    ),
    dict(
        key='printing', label='3D హౌసింగ్', visual='split',
        image='printer_3d.jpg',
        head=[('3D కాంక్రీట్ ప్రింటింగ్', False, 78), ('177 ఇళ్లు • ₹14 కోట్లు', True, 78)],
        chip='పైలట్ ప్రాజెక్ట్',
        footnote='బుర్రిపాలెం, ఒబులనాయుడుపాలెం గ్రామాల్లో',
    ),
    dict(
        key='target', label='లక్ష్యం', visual='time',
        image='printed_wall.jpg',
        head=[('6 నెలల్లో', False, 96), ('పూర్తి చేయాలనే లక్ష్యం', True, 76)],
        chip='నిర్మాణ లక్ష్యం',
        footnote='177 ఇళ్ల నిర్మాణానికి లక్ష్యంగా నిర్ణయించిన సమయం',
    ),
    dict(
        key='future', label='ప్రస్తుతం vs భవిష్యత్', visual='compare',
        head=[('ప్రస్తుత 3 లక్షలు', False, 82), ('మరో 3 లక్షలు అవకాశం', True, 82)],
        chip='ప్రస్తుత మంజూరు • భవిష్యత్ దశ',
        footnote='నిర్మాణం పూర్తయిన తర్వాత అవకాశం ఉందని కేంద్ర మంత్రి వెల్లడి',
    ),
    dict(
        key='cta', label='జనసేవ న్యూస్', visual='cta',
        head=[('మీ అభిప్రాయం', False, 84), ('కామెంట్ చేయండి', True, 88)],
        chip='మరిన్ని AP వార్తల కోసం ఫాలో అవ్వండి',
        footnote=PAYOFF,
    ),
]

assert len(SCENES) == len(SCHEDULE) == len(SUBS) == len(VO_IDS)


def scene_seconds():
    """Exact on-screen duration of every scene, in seconds."""
    return [f / FPS for f in SCHEDULE]


def scene_start(index):
    return sum(SCHEDULE[:index]) / FPS


def proportional_cues():
    """Fallback subtitle timing: spread each scene's cues across its own runtime.

    Returns absolute cue windows (scene offset included), matching the shape of
    make_video.snap_cues() so the two are interchangeable.
    """
    out = []
    for i, cues in enumerate(SUBS):
        weights = [c[1] for c in cues]
        total = sum(weights)
        t, rows = scene_start(i), []
        for (text, w, hi) in cues:
            dur = SCHEDULE[i] / FPS * w / total
            rows.append((text, round(t, 3), round(t + dur, 3), hi))
            t += dur
        out.append(rows)
    return out
