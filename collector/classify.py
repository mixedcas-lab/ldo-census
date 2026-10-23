"""Classification and spec extraction for LDO / linear voltage regulator papers.

Pure functions (no network, no files) so they can be unit-tested and re-run over the
cached records whenever the rules change. Abstracts are inputs only; they are never
written to the output.
"""
import math
import re

I = re.IGNORECASE

# ---------------------------------------------------------------- relevance
LDO_PAT = re.compile(
    r"\bLDOs?\b|low[- ]drop[- ]?out|\bD-?LDOs?\b|\bA?DLDOs?\b|linear (?:voltage )?regulators?|"
    r"(?:capacitor|cap)[- ]?less (?:LDO|regulator)|output[- ]capacitor[- ]?(?:less|free)|\bOCL[- ]LDO", I)
# a "voltage regulator" alone may be switched; keep it only when the title says it is linear or digital-linear
LINEAR_HINT = re.compile(r"\bLDO|low[- ]drop|\blinear\b|capacitor[- ]?less|capless|output[- ]capacitor|pass (?:transistor|device)|"
                         r"\bPSRR|quiescent|dropout|flipped voltage follower|\bFVF\b", I)
NOT_LDO = re.compile(r"switched[- ]capacitor|\bSC\b (?:converter|regulator)|inductor|buck|boost|DC[- ]?DC|resonant|"
                     r"charge pump regulator|\bIVR\b|magnetic", I)
HOST = re.compile(r"\b(?:processor|SoC|system|subsystem|microcontroller|\bMCU\b|transceiver|receiver|PMIC|power management unit|"
                  r"\bPMU\b|energy harvest\w*|sensor node|platform|chip)s?\b.*\b(?:with|using|featuring|including|integrat\w*)\b", I)

NON_PAPER = re.compile(
    r"^(front cover|back cover|table of contents|contents|author index|index|"
    r"call for papers|editorial|guest editorial|reviewers|session \d+ overview|"
    r"(?:tutorials?|short course|evening (?:event|session)|forum|panel)(?=\s*:|\s*$)|"
    r"(ieee )?(transactions|journal) .*information|blank page|copyright)\b", I)


def relevance(title, abstract):
    """Return 'core', 'related' or None."""
    t = title or ""
    m = LDO_PAT.search(t) or (re.search(r"voltage regulator", t, I) and LINEAR_HINT.search(t))
    if m:
        if NOT_LDO.search(t) and not re.search(r"\bLDO|low[- ]drop|\blinear (?:voltage )?regulator", t, I):
            return None
        h = HOST.search(t)
        if h and h.start() < (m.start() if hasattr(m, "start") else 0):
            return "related"
        return "core"
    if re.search(r"\bLDOs?\b|low[- ]dropout regulator", abstract or "", I) and not NOT_LDO.search(t):
        return "related"
    return None


# ------------------------------------------------------------- type / architecture / application
def ldo_type(title, abstract):
    text = (title or "") + " " + (abstract or "")
    if re.search(r"hybrid|analog[- ]assisted|digitally[- ]assisted|analog[- ]digital|mixed[- ]mode|dual[- ]loop.*digital", text, I) and \
            re.search(r"digital", text, I):
        return "Hybrid"
    if re.search(r"\bD-?LDO|digital(?:ly[- ]controlled)? (?:LDO|low[- ]dropout|linear regulator)|all[- ]digital", text, I):
        return "Digital"
    return "Analog"


ARCH_RULES = [
    ("Capacitor-less",    r"capacitor[- ]?less|cap[- ]?less|output[- ]capacitor[- ]?(?:less|free)|\bOCL\b|on[- ]chip capacitor|fully[- ]integrated"),
    ("FVF",               r"flipped[- ]voltage[- ]follower|\bFVF\b"),
    ("Adaptive biasing",  r"adaptive(?:ly)?[- ]bias|dynamic(?:ally)?[- ]bias|load[- ]tracking|adaptive[- ]current"),
    ("NMOS pass",         r"\bNMOS (?:pass|power)|N-?type pass|source[- ]follower pass"),
    ("Event-driven",      r"event[- ]driven|asynchronous|self[- ]timed|clock[- ]less"),
    ("Distributed",       r"distributed|multi[- ]?(?:phase|core|LDO)|parallel LDO"),
    ("Ripple cancellation", r"ripple[- ]cancel|feedforward|feed[- ]forward|\bFFRC\b"),
    ("Time-domain",       r"time[- ]domain|\bVCO[- ]based|\bTDC\b|PWM[- ]based"),
    ("Charge-pump gate",  r"charge[- ]pump"),
    ("Bulk-driven",       r"bulk[- ]driven|body[- ]driven"),
]
ARCH_RX = [(n, re.compile(p, I)) for n, p in ARCH_RULES]


def architectures(title, abstract):
    def scan(text):
        return [n for n, rx in ARCH_RX if rx.search(text or "")]
    tags = scan(title)
    if abstract:
        first = " ".join(re.split(r"(?<=[.!?])\s+", abstract)[:2])
        for t in scan(first):
            if t not in tags:
                tags.append(t)
    return tags


APP_RULES = [
    ("Digital/SoC",        r"processor|\bCPU\b|\bGPU\b|\bSoC\b|\bSRAM\b|memory|\bDVFS\b|digital load|logic|near[- ]threshold|power[- ]gating|computing"),
    ("Analog/RF supply",   r"\bPSRR\b|low[- ]noise|noise[- ]sensitive|\bRF\b|\bPLL\b|\bVCO\b|\bADC\b|mixed[- ]signal|transceiver"),
    ("IoT/low-power",      r"\bIoT\b|nA\b|nano[- ]?ampere|ultra[- ]low[- ]power|energy[- ]harvest|wearable|implant|biomedical|sensor node|battery"),
    ("Automotive/high-V",  r"automotive|high[- ]voltage|\bHV\b|\b(?:[2-9]\d|[1-9]\d\d)(?:\.\d+)?\s*-?\s*V\b"),
    ("Power management",   r"\bPMIC\b|\bPMU\b|power management|dc[- ]?dc|post[- ]regulat"),
]
APP_RX = [(n, re.compile(p, I)) for n, p in APP_RULES]
CAL_RX = re.compile(r"calibrat|trimm|background (?:correction|estimation)", I)


def applications(title, abstract):
    text = (title or "") + " " + (abstract or "")
    return [n for n, rx in APP_RX if rx.search(text)]


def has_calibration(title, abstract):
    return bool(CAL_RX.search((title or "") + " " + (abstract or "")))


# ------------------------------------------------------------- spec parsing
NUM = r"(\d+(?:\.\d+)?)"
NEG = r"([−–-]\s?\d+(?:\.\d+)?)"
_SI = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
       "m": 1e-3, "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
_FIXES = [(re.compile(r"(\d)\.\s(\d)"), r"\1.\2"), (re.compile(r"(\d)\s*-?\s*mu(m|W|A|V|s|F)\b"), r"\1 µ\2"),
          (re.compile(r"([µμ])\s+([mAVFs])\b"), r"\1\2"), (re.compile(r"\\?hbox\s*"), ""),
          (re.compile(r"~|\b(?:boldsymbol|mathrm|mathbf)\s*"), " "), (re.compile(r"(\d)\s+([µμnpm]?[AVF]\b)"), r"\1 \2")]


def _norm(text):
    for rx, rep in _FIXES:
        text = rx.sub(rep, text)
    return text


def _si(v, pre):
    pre = (pre or "").replace("u", "µ")
    return float(v) * _SI.get(pre, _SI.get(pre.lower(), 1.0))   # case-insensitive patterns may hand over "P", "N"


ILOAD_RX = [   # maximum load current
    re.compile(r"(?:maximum|max\.?|peak|full|rated)[- ]load[- ]current[^.;\d]{0,25}?(?:of\s+|up to\s+|is\s+)?" + NUM + r"\s*-?\s*([µμunm]?)A\b", I),
    re.compile(r"load[- ]current(?:\s+range)?[^.;\d]{0,20}?(?:of\s+|up to\s+|from\s+[\d.]+\s*[µμunm]?A\s+to\s+)" + NUM + r"\s*-?\s*([µμunm]?)A\b", I),
    re.compile(r"(?:up to|maximum of)\s+" + NUM + r"\s*-?\s*([µμunm]?)A\b", I),
    re.compile(r"(?:[\d.]+\s*[µμunm]?A\s*(?:-|–|to)\s*)" + NUM + r"\s*-?\s*([µμunm]?)A\s+(?:load|output)", I),
    re.compile(NUM + r"\s*-?\s*([µμunm]?)A\s+(?:maximum\s+)?(?:load|output)[- ]current", I),
    re.compile(NUM + r"\s*-?\s*([µμunm]?)A[- ](?:[\w-]+[- ]){0,2}?(?:LDO|low[- ]dropout|DLDO|regulator)", I),
    re.compile(NUM + r"\s*-?\s*([µμunm]?)A\s+(?:maximum|max\.?|peak)\s+(?:output\s+|load\s+)?current", I),
    re.compile(NUM + r"\s*-?\s*([µμunm]?)A[- ](?:output\s+)?current[- ]capabilit", I),
    re.compile(r"(?:current capability|current capacit\w*|deliver\w*|supplies|supports)[^.;\d]{0,20}?(?:of\s+|up to\s+)?" + NUM + r"\s*-?\s*([µμunm]?)A\b", I),
]
# the size of the load step, used for I_load,max only when nothing else is reported
ILOAD_STEP_RX = re.compile(NUM + r"\s*-?\s*([µμunm]?)A(?:\s*/\s*[\d.]+\s*-?\s*[pnuµμ]?s)?\s+(?:full[- ])?load[- ](?:step|transient|transition|change|jump)", I)
IQ_RX = [
    re.compile(r"(?:quiescent|ground|standby)[- ]current(?:\s*\(I_?Q\))?[^.;\d]{0,25}?(?:of\s+|is\s+|only\s+)?" + NUM + r"\s*-?\s*([µμunp]?)A\b", I),
    re.compile(NUM + r"\s*-?\s*([µμunp]?)A\s+(?:of\s+)?(?:the\s+)?(?:total\s+)?quiescent", I),
    re.compile(r"\bI_?Q\b\s*(?:=|of|is)?\s*" + NUM + r"\s*-?\s*([µμunp]?)A\b", I),
]
DROPOUT_RX = [
    re.compile(r"dropout(?:\s+voltage)?[^.;\d]{0,20}?(?:of\s+|is\s+)?" + NUM + r"\s*-?\s*(m?)V\b", I),
    re.compile(NUM + r"\s*-?\s*(m?)V\s+dropout", I),
]
VIN_RX = re.compile(r"(?:input|supply)[- ]voltage[^.;\d]{0,25}?(?:of\s+|from\s+|range\s+of\s+)?(?:[\d.]+\s*(?:V\s*)?(?:-|–|to)\s*)?" + NUM + r"\s*-?\s*V\b|"
                    r"\bV_?IN\b[^.;\d]{0,10}?(?:[\d.]+\s*(?:V\s*)?(?:-|–|to)\s*)?" + NUM + r"\s*-?\s*V\b", I)
VOUT_RX = re.compile(r"(?:output[- ]voltage|regulated (?:output|voltage)|\bV_?OUT\b)[^.;\d]{0,25}?(?:of\s+|is\s+)?" + NUM + r"\s*-?\s*V\b|" +
                     NUM + r"\s*-?\s*V\s+(?:regulated\s+)?output", I)
PSRR_RX = re.compile(r"(?:PSRR?\b|power[- ]supply rejection(?: ratio)?)[^.;\d−–-]{0,25}?(?:of\s+|is\s+|better than\s+|below\s+)?" +
                     r"([−–-]?\s?\d+(?:\.\d+)?)\s*-?\s*dB(?:\s*(?:at|@|up to)\s*" + NUM + r"\s*-?\s*([kMG]?)Hz)?|" +
                     r"([−–-]?\s?\d+(?:\.\d+)?)\s*-?\s*dB[- ](?:(?:worst[- ]case\s+)?PSRR?\b|(?:worst[- ]case\s+)?power[- ]supply rejection)(?:\s*(?:at|@|up to)\s*" + NUM + r"\s*-?\s*([kMG]?)Hz)?", I)
# "PSRR at 1 MHz is -30 dB": frequency before value
PSRR_FFIRST_RX = re.compile(r"(?:PSRR?\b|power[- ]supply rejection(?: ratio)?)\s+(?:at|@)\s+" + NUM + r"\s*-?\s*([kMG]?)Hz\s+(?:is|of|=|was|reaches)\s+"
                            r"([−–-]?\s?\d+(?:\.\d+)?)\s*-?\s*dB", I)
DV_RX = [   # load-transient droop / undershoot
    re.compile(r"(?:undershoot|droop|voltage dip|transient (?:response|variation|spike)|output (?:voltage )?(?:variation|deviation|spike))[^.;\d]{0,30}?"
               r"(?:of\s+|is\s+|only\s+|within\s+|less than\s+|below\s+)?" + NUM + r"\s*-?\s*(m?)V\b", I),
    re.compile(NUM + r"\s*-?\s*(m?)V(?:P-?P|pp)?\s+(?:of\s+)?(?:voltage\s+|output\s+)?(?:undershoot|droop|dip|transient)", I),
    re.compile(r"undershoot(?:\s*(?:/|and)\s*overshoot)?(?:\s+(?:at the output|voltages?))?\s+(?:of|are|is|were|was)\s+" + NUM + r"(?:\s*(?:/|and)\s*[\d.]+)?\s*-?\s*(m?)V\b", I),
]
SETTLE_RX = re.compile(r"(?:settling|recovery|response) time[^.;\d]{0,20}?(?:of\s+|is\s+)?" + NUM + r"\s*-?\s*([pnuµμm]?)s\b|" +
                       NUM + r"\s*-?\s*([pnuµμm]?)s\s+(?:settling|recovery|response) time", I)
COUT_RX = re.compile(NUM + r"\s*-?\s*([pnuµμ])F\s+(?:on[- ]chip\s+|off[- ]chip\s+|output\s+|load\s+)*(?:output\s+)?capacit", I)
CE_RX = re.compile(r"current efficiency[^.;\d]{0,20}?(?:of\s+|is\s+)?" + NUM + r"\s*%|" + NUM + r"\s*%\s+current efficiency", I)
FOM_RX = re.compile(r"(?:FoM|figure[- ]of[- ]merit)[^.;\d]{0,30}?(?:of\s+|is\s+)?" + NUM + r"\s*-?\s*([afpnµμ]?)s\b|" +
                    NUM + r"\s*-?\s*([afpnµμ]?)s\s+(?:FoM|figure[- ]of[- ]merit)", I)
DENSITY_RX = re.compile(NUM + r"\s*-?\s*A\s*/\s*mm\s*(?:2|²)", I)
NODE_NM_RX = re.compile(r"(?<![\w.])(\d{1,3})\s*-?\s*nm\b", I)
NODE_UM_RX = re.compile(r"(?<![\w.])(0\.\d{1,3})\s*-?\s*[µμu]m\b|(?<![\w.])([1-3](?:\.\d)?)\s*-?\s*[µμu]m\s+(?:\w+\s+){0,2}"
                        r"(?:CMOS|BiCMOS|process|technology|SOI|BCD)", I)
AREA_RX = re.compile(NUM + r"\s*-?\s*mm\s*(?:2|²|\^2)(?!\s*/)", I)


def _first(rxs, *texts):
    for text in texts:
        for rx in rxs:
            m = rx.search(text or "")
            if m:
                return m
    return None


def _pair(m):
    """(value, prefix) from the first filled alternative of a match."""
    g = m.groups()
    for i in range(0, len(g) - 1):
        if g[i] is not None and re.match(r"^[−–-]?\s?\d", g[i]):
            return g[i], g[i + 1]
    return None, None


def parse_specs(title, abstract):
    t, a = _norm(title or ""), _norm(abstract or "")
    out = {}
    m = _first(ILOAD_RX, t, a) or ILOAD_STEP_RX.search(a) or ILOAD_STEP_RX.search(t)
    if m:
        v = _si(m.group(1), m.group(2))
        if 1e-7 <= v <= 100:
            out["il"] = v
    m = _first(IQ_RX, t, a)
    if m:
        v = _si(m.group(1), m.group(2))
        if 1e-12 <= v <= 0.1:
            out["iq"] = v
    m = _first(DROPOUT_RX, t, a)
    if m:
        v = float(m.group(1)) * (1e-3 if m.group(2) else 1)
        if 0.005 <= v <= 2:
            out["vdo"] = v
    m = VIN_RX.search(a) or VIN_RX.search(t)
    if m:
        v = float(m.group(1) or m.group(2))
        if 0.2 <= v <= 60:
            out["vin"] = v
    m = VOUT_RX.search(a) or VOUT_RX.search(t)
    if m:
        v = float(m.group(1) or m.group(2))
        if 0.1 <= v <= 60:
            out["vout"] = v
    m = PSRR_RX.search(t) or PSRR_RX.search(a)
    mf = PSRR_FFIRST_RX.search(t) or PSRR_FFIRST_RX.search(a)
    if mf and (not m or mf.start() <= m.start()):
        v = -abs(float(re.sub(r"[−–\s-]", "", mf.group(3))))
        if -150 <= v <= -5:
            out["psrr"], out["psrr_f"] = v, _si(mf.group(1), mf.group(2))
        m = None
    if m:
        if m.group(1):
            val, f, pre = m.group(1), m.group(2), m.group(3)
        else:
            val, f, pre = m.group(4), m.group(5), m.group(6)
        v = -abs(float(re.sub(r"[−–\s-]", "", val)))
        if -150 <= v <= -5:
            out["psrr"] = v
            if f:
                out["psrr_f"] = _si(f, pre)
    m = _first(DV_RX, t, a)
    if m:
        v = float(m.group(1)) * (1e-3 if m.group(2) else 1)
        if 1e-4 <= v <= 0.6:
            out["dv"] = v
    m = SETTLE_RX.search(a) or SETTLE_RX.search(t)
    if m:
        val, pre = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        out["ts"] = _si(val, pre)
    if re.search(r"capacitor[- ]?less|cap[- ]?less|output[- ]capacitor[- ]?(?:less|free)|\bOCL\b", t + " " + a, I):
        out["capless"] = 1
    m = COUT_RX.search(a) or COUT_RX.search(t)
    if m:
        out["cout"] = _si(m.group(1), m.group(2))
    m = CE_RX.search(a) or CE_RX.search(t)
    if m:
        v = float(m.group(1) or m.group(2))
        if 50 <= v <= 100:
            out["ce"] = v
    m = FOM_RX.search(t) or FOM_RX.search(a)
    if m:
        val, pre = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        v = _si(val, pre)
        if 1e-20 <= v <= 1e-6:
            out["fom"] = v
    m = DENSITY_RX.search(t) or DENSITY_RX.search(a)
    if m:
        out["density"] = float(m.group(1))
    m = NODE_NM_RX.search(t) or NODE_NM_RX.search(a)
    if m and 2 <= int(m.group(1)) <= 500:
        out["node"] = int(m.group(1))
    else:
        m = NODE_UM_RX.search(t) or NODE_UM_RX.search(a)
        if m:
            out["node"] = int(round(float(m.group(1) or m.group(2)) * 1000))
    m = AREA_RX.search(a) or AREA_RX.search(t)
    if m:
        out["area"] = float(m.group(1))
    return {k: float("%.6g" % v) if isinstance(v, float) else v for k, v in out.items()}   # 1e-5, not 9.999999999999999e-06


def spec_sources(title, abstract):
    """parse_specs() plus where each value came from: {"key": "t" | "a"}."""
    full = parse_specs(title, abstract)
    only_title = parse_specs(title, "")
    return full, {k: ("t" if only_title.get(k) == v else "a") for k, v in full.items()}


def ldo_fom(specs):
    """Hazucha's FoM = Cout · ΔVout · Iq / Iload,max² (s); needs all four."""
    c, dv, iq, il = specs.get("cout"), specs.get("dv"), specs.get("iq"), specs.get("il")
    return c * dv * iq / il ** 2 if c and dv and iq and il else None


def derived(specs):
    d = {}
    f = ldo_fom(specs)
    if f is not None and "fom" not in specs:
        d["fom_calc"] = float("%.3g" % f)
    if specs.get("iq") and specs.get("il") and "ce" not in specs:
        d["ce_calc"] = round(100 * specs["il"] / (specs["il"] + specs["iq"]), 4)
    return d


# ------------------------------------------------------------- affiliations
ORG_HINT = re.compile(r"universit|institut|college|school|KAIST|POSTECH|UNIST|DGIST|GIST|\bETH\b|EPFL|\bMIT\b|"
                      r"laborator|\blabs?\b|inc\b|ltd|corp|company|co\.|electronics|semiconductor|technolog|"
                      r"research|centre|center|academy|imec|tsmc|samsung|sk hynix|intel|mediatek|qualcomm|"
                      r"apple|google|huawei|broadcom|analog devices|texas instruments", I)


US_STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK "
             "OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC").split()
COUNTRY_ALIASES = {"thenetherlands": "Netherlands", "netherlands": "Netherlands", "holland": "Netherlands",
                   "uk": "UK", "unitedkingdom": "UK", "england": "UK", "scotland": "UK", "greatbritain": "UK",
                   "republicofsingapore": "Singapore", "hongkong": "Hong Kong", "hongkongsar": "Hong Kong",
                   "rocchina": "Taiwan", "taiwanroc": "Taiwan", "taiwan,roc": "Taiwan", "roc": "Taiwan",
                   "korearepublicof": "South Korea", "southkorea": "South Korea", "usa": "USA", "us": "USA"}
COUNTRY_ALIASES.update({st.lower(): "USA" for st in US_STATES})
COUNTRY_ALIASES.update({"uae": "United Arab Emirates", "türkiye": "Turkey", "turkiye": "Turkey", "macao": "Macau", "hk": "Hong Kong",
                        "kr": "South Korea", "korea": "South Korea", "republicofkorea": "South Korea", "korea(south)": "South Korea",
                        "sg": "Singapore", "taiwan(roc)": "Taiwan", "prc": "China", "prchina": "China", "peoplesrepublicofchina": "China",
                        "people'srepublicofchina": "China", "unitedstates": "USA", "unitedstatesofamerica": "USA", "california": "USA",
                        "oregon": "USA", "texas": "USA", "massachusetts": "USA", "czechia": "Czech Republic", "russianfederation": "Russia"})
COUNTRIES = {"USA", "China", "South Korea", "Taiwan", "Netherlands", "Japan", "Belgium", "Canada", "Germany", "Italy", "India",
             "Switzerland", "Singapore", "Spain", "UK", "Ireland", "Austria", "France", "Sweden", "Finland", "Portugal", "Hong Kong",
             "United Arab Emirates", "Norway", "Iran", "Israel", "Saudi Arabia", "Egypt", "Argentina", "Australia", "Brazil", "Denmark",
             "Turkey", "Qatar", "Malaysia", "Vietnam", "Greece", "Colombia", "Macau", "Lebanon", "Romania", "Hungary", "Tunisia",
             "Czech Republic", "Philippines", "Poland", "Mexico", "Russia", "Chile", "Bahrain", "Iraq", "Indonesia", "Pakistan",
             "Thailand", "Kazakhstan", "New Zealand", "Estonia", "Mauritius", "Ukraine", "Slovenia", "Slovakia", "Serbia", "Croatia",
             "Bulgaria", "Luxembourg", "Cyprus", "Morocco", "Algeria", "Jordan", "Kuwait", "Oman", "Nigeria", "South Africa", "Kenya",
             "Bangladesh", "Sri Lanka", "Nepal", "Peru", "Uruguay", "Venezuela", "Ecuador", "Iceland", "Lithuania", "Latvia",
             "Belarus", "Armenia"}
# affiliation parts that name a city or an institution instead of a country
PLACE_COUNTRY = [(re.compile(p, I), c) for p, c in (
    (r"\b(?:delft|eindhoven|twente|enschede)\b", "Netherlands"), (r"\b(?:dallas|san diego|corvallis|san jose|santa clara)\b", "USA"),
    (r"\b(?:daejeon|seoul|pohang|ulsan|suwon|samsung|sk hynix|kaist|postech)\b", "South Korea"),
    (r"\b(?:beijing|shanghai|tsinghua|peking|zhejiang|fudan|xi'?an|nanjing|shenzhen|hangzhou|chengdu)\b", "China"),
    (r"\b(?:tokyo|osaka|kyoto|hiroshima)\b", "Japan"), (r"\bmaca[uo]\b", "Macau"), (r"\bnational taiwan\b|\bhsinchu\b|\btaipei\b", "Taiwan"),
    (r"\btu berlin\b|\bbosch\b|\bmunich\b", "Germany"), (r"\bcesson|\bparis\b|\bgrenoble\b", "France"),
    (r"\b(?:oregon state|brigham young|university of utah|emory|purdue|university of florida|university of washington|northeastern|"
     r"intel|qualcomm)\b", "USA"), (r"\banalog devices canada\b", "Canada"))]


def _country(parts, aff):
    """The country of an affiliation, or None: the parts from the end first, then known cities and institutions."""
    for raw in reversed(parts):
        c = re.sub(r"\s+\d[\d\- ]*$", "", raw).strip()
        c = COUNTRY_ALIASES.get(re.sub(r"[\s.]", "", c).lower(), c)
        if c.isupper() and len(c) > 3:
            c = c.title()                    # "MEXICO", "SPAIN"
        if c in COUNTRIES:
            return c
    for rx, c in PLACE_COUNTRY:
        if rx.search(aff):
            return c
    return None


def org_and_country(aff):
    if not aff:
        return None, None
    parts = [p.strip() for p in aff.split(",") if p.strip()]
    if not parts:
        return None, None
    country = _country(parts, aff)
    org = None
    for p in parts:
        if ORG_HINT.search(p) and not re.match(r"(department|dept|school of|faculty|division)\b", p, I):
            org = p
            break
    if org is None:
        org = parts[1] if len(parts) > 2 else parts[0]
    return org, country


# ------------------------------------------------------------- dates
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_month(pubdate, year):
    """'19-23 Feb. 2025' -> '2025-02'; falls back to 'YYYY'."""
    s = (pubdate or "").lower()
    y = None
    years = re.findall(r"(?:19|20)\d{2}", s)
    if years:
        y = years[-1]
    elif year:
        y = str(year)
    mon = None
    for tok in re.findall(r"[a-z]{3,}", s):
        if tok[:3] in MONTHS:
            mon = MONTHS[tok[:3]]
            break
    if y and mon:
        return "%s-%02d" % (y, mon)
    return y or ""
