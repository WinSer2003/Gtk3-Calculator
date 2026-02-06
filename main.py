import gi, re, math
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, GtkLayerShell, Gdk

# yksikkökarttö
unit_map = {
    "nm":1e-9, "µm":1e-6, "um":1e-6, "mm":1e-3, "cm":1e-2,
    "m":1, "km":1000, "mi":1609.34, "ft":0.3048, "yd":0.9144, "ly":9.461e15,
    "mg":1e-6, "g":1e-3, "kg":1, "t":1000,"lb":2.204623,
    "ns":1e-9, "µs":1e-6, "us":1e-6, "ms":1e-3, "s":1, "min":60, "h":3600, "day":86400, "yr":31536000,
    "c":1, "°c":1, "f":"f", "°f":"f", "k":"k",
    "a":1, "v":1, "w":1,
    "j":1, "kj":1000, "cal":4.184,
    "pa":1, "kpa":1000, "atm":101325, "bar":1e5,
    "sv":1, "msv":1e-3, "usv":1e-6, "nsv":1e-9, "rad":0.01, "r":0.01,
    "bq":1, "kbq":1e3, "mbq":1e6, "gbq":1e9, "tbq":1e12, "pbq":1e15,
    "pci":0.037, "nci":37, "uci":3.7e4, "mci":3.7e7, "ci":3.7e10, "kci":3.7e13,
    "cps":1, "cpm":1/60, "":0.0
}

category = {}
for k in unit_map:
    if k in ["nm","µm","um","mm","cm","m","km","mi","ft","yd","ly"]: category[k]="length"
    elif k in ["mg","g","kg","t","lb"]: category[k]="mass"
    elif k in ["ns","µs","us","ms","s","min","h","day","yr"]: category[k]="time"
    elif k in ["c","°c","f","°f","k"]: category[k]="temperature"
    elif k in ["a","v","w"]: category[k]="electric"
    elif k in ["j","kj","cal"]: category[k]="energy"
    elif k in ["pa","kpa","atm","bar"]: category[k]="pressure"
    elif k in ["sv","msv","usv","nsv","rad","r"]: category[k]="radiation"
    elif k in ["bq","kbq","mbq","gbq","tbq","pbq","pci","nci","uci","mci","ci","kci","cps","cpm"]: category[k]="radioactive-decay"

category_icons = {
    "radiation":"",
    "length":"",
    "mass":"",
    "time":"",
    "temperature":"",
    "energy":"",
    "pressure":"",
    "electric":"",
    "number":"",
    "radioactive-decay":""
}

# SI-muunnos
def convert_to_si(expr):
    expr = expr.replace(" ", "")
    def repl(m):
        val = float(m.group("num"))
        unit = m.group("unit")
        if not unit:
            return str(val)
        u = unit.lower()
        if u in ["f","°f"]:
            return str((val-32)*5/9)
        if u == "k":
            return str(val-273.15)
        if u in unit_map and isinstance(unit_map[u], (int,float)):
            return str(val*unit_map[u])
        return str(val)
    return re.sub(r"(?P<num>-?\d+(\.\d*)?)(?P<unit>[a-z°µ]+)?", repl, expr)

def detect_category(expr):
    expr_units = re.findall(r"[a-z°µ]+", expr.lower())
    if not expr_units:
        return "number"
    for u in expr_units:
        if u in ["sv","msv","usv","nsv","rad","r"]:
            return "radiation"
    for u in expr_units:
        if u in category:
            return category[u]
    if {"a","v"} <= set(expr_units):
        return "electric"
    return "number"

# LD lasku
def radiation_ld(value_sv):
    ld50 = 4.5  # Sv
    ld100 = 10  # Sv
    if value_sv < 0.1:
        return "LD negligible"
    percent_50 = min(100, max(0, (value_sv / ld50) * 50))
    percent_100 = min(100, max(0, (value_sv / ld100) * 100))
    return f"LD50/30 ≈ {percent_50:.1f}%\nLD100/30 ≈ {percent_100:.1f}%"

# enhanced eval
def enhanced_eval(expr):
    expr = expr.replace("^", "**")
    # inverse square law
    match = re.match(r"inverse\s+(-?\d+(\.\d*)?[a-z°µ]*)\s*-\s*(\d+(\.\d*)?[a-z°µ]*)", expr.lower())
    if match:
        dose_str, _, dist_str, _ = match.groups()
        dose = float(convert_to_si(dose_str))
        dist = float(convert_to_si(dist_str))
        if dist != 0:
            return dose / (dist**2)
        else:
            return "err"
    # normaali eval
    try:
        val = eval(convert_to_si(expr), {"__builtins__":{}, "sqrt": math.sqrt, "pow": math.pow})
        return val
    except:
        return "err"

def calc_expr(txt):
    parts = txt.split("|")
    results = []
    for part in parts:
        try:
            val = enhanced_eval(part)
            results.append((val, part))
        except:
            results.append(("err", part))
    return results

def format_result(value, unit_type):
    res=[]
    if unit_type=="length":
        m=value
        res.append(f"{m/1000:.3f} km ")
        res.append(f"{m:.2f} m ")
        res.append(f"{m/0.3048:.2f} ft ")
        res.append(f"{m/0.9144:.2f} yd  ")
        res.append(f"{m/1609.34:.2f} mi ")
        if m>=9.461e15: res.append(f"{m/9.461e15:.6f} ly")
    elif unit_type=="mass":
        kg=value
        res.append(f"{kg:.2f} kg")
        if kg>=1e-3: res.append(f"{kg*1000:.2f} g")
        if kg>=1e-6: res.append(f"{kg*1e6:.2f} mg")
        if kg>=1000: res.append(f"{kg/1000:.2f} t")
        lb = kg*2.20462
        res.append(f"{lb:.2f} lb")
    elif unit_type=="time":
        s=value
        res.append(f"{s:.2f} s")
        if s>=3600 and s<86400: res.append(f"{s/3600:.2f} Hours")
        if s>=60 and s<3600: res.append(f"{s/60:.2f} minutes")
        if s>=1e-3 and s<1: res.append(f"{s*1000:.2f} milliseconds")
        if s>=1e-6 and s<1e-3: res.append(f"{s*1e6:.2f} microseconds")
        if s>=1e-9 and s<1e-6: res.append(f"{s*1e9:.2f} nanoseconds")
        if s>=86400 and s<31536000: res.append(f"{s/86400:.2f} days")
        if s>=31536000 and s<31536000*10: res.append(f"{s/31536000:.2f} years")
        if s>=31536000*10: res.append(f"{s/31536000:.2f} decades")
    elif unit_type=="radioactive-decay":
        bq=value
        if bq < 1e5: res.append(f"{bq:.2f} Bq")
        if bq>=1e3 and bq<1e7: res.append(f"{bq/1e3:.2f} kBq")
        if bq>=1e6 and bq<1e10: res.append(f"{bq/1e6:.2f} MBq")
        if bq>=1e9 and bq<1e12: res.append(f"{bq/1e9:.2f} GBq")
        if bq>=1e12 and bq<1e15: res.append(f"{bq/1e12:.2f} TBq")
        if bq>=1e15: res.append(f"{bq/1e15:.2f} PBq")
        ci=bq/3.7e10
        res.append(f"{ci:.2f} Ci")
        if ci>=1e-3 and ci<1e-1: res.append(f"{ci*1e3:.2f} mCi")
        if ci>=1e-6 and ci<1e-3: res.append(f"{ci*1e6:.2f} µCi")
        if ci>=1e-9 and ci<1e-6: res.append(f"{ci*1e9:.2f} nCi")
        cps=bq
        if cps<=1e5: res.append(f"{cps:.2f} CPS")
        if cps<=1e8 and cps>=1e2: res.append(f"{cps/1e3:.2f} kCPS")
        if cps>=1e6 and cps<1e9: res.append(f"{cps/1e6:.2f} MCPS")
        cpm=bq*60
        if cpm<=1e5: res.append(f"{cpm:.2f} CPM")
        if cpm<=1e8: res.append(f"{cpm/1e3:.2f} kCPM")
    elif unit_type=="temperature":
        c=value
        res.append(f"{c:.2f} °C")
        res.append(f"{c*9/5+32:.2f} °F")
        res.append(f"{c+273.15:.2f} K")
    elif unit_type=="radiation":
        sv=value
        res.append(f"{sv:.2f} Sv")
        if sv>=1e-3: res.append(f"{sv*1e3:.2f} mSv")
        if sv>=1e-6: res.append(f"{sv*1e6:.2f} µSv")
        if sv>=1e-9: res.append(f"{sv*1e9:.2f} nSv")
        rad=sv/0.01
        res.append(f"{rad:.2f} rad")
        res.append(f"{rad:.2f} R")
    elif unit_type=="energy":
        j=value
        res.append(f"{j:.2f} J")
        if j>=1000: res.append(f"{j/1000:.2f} kJ")
        cal=j/4.184
        res.append(f"{cal:.2f} cal")
    elif unit_type=="pressure":
        pa=value
        res.append(f"{pa:.2f} Pa")
        if pa>=1000: res.append(f"{pa/1000:.2f} kPa")
        res.append(f"{pa/101325:.4f} atm")
        res.append(f"{pa/1e5:.2f} bar")
    
    elif unit_type=="electric":
        res.append(f"{value:.2f} W")
    else:
        res.append(str(value))
    return "\n".join(res)

# GUI
class SmartSI(Gtk.Window):
    def __init__(self):
        super().__init__()
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        for edge in [GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT]:
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 8)
        GtkLayerShell.set_keyboard_interactivity(self, True)

        self.set_decorated(False)
        self.set_resizable(True)
        self.set_skip_taskbar_hint(True)
        self.set_default_size(250, 300)

        css = b"""
        window { background: rgba(10,10,30,0.85); border-radius: 14px; }
        entry { background: rgba(20,20,40,0.9); color: #aaf0ff; border-radius:10px; padding:8px; font-size:18px; }
        label { color: #66ddff; font-size:16px; padding-left:6px; }
        entry completion {
    background: rgba(15,15,30,0.95);
    border-radius: 10px;
    padding: 6px;
    }

    entry completion treeview {
        background: transparent;
        color: #aaf0ff;
        font-size: 15px;
    }

    entry completion treeview row {
        padding: 6px;
        border-radius: 6px;
    }

    entry completion treeview row:selected {
        background: rgba(80,120,255,0.35);
        color: #ffffff;
    }
    entry completion treeview row:hover {
    background: rgba(80,120,255,0.2);
}


        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(10); box.set_margin_bottom(10)
        box.set_margin_start(12); box.set_margin_end(12)
        self.add(box)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("22km+22km | 7A*20V | 3W*2 | 22nSv+5µSv | inverse 20mSv-2m | sqrt(16) | 2^3 | 10Sv")
        self.entry.connect("changed", self.live_process)
        self.result = Gtk.Label(label="")
        self.result.set_xalign(0)
        self.result.set_line_wrap(True)
        box.pack_start(self.entry, True, True, 0)
        box.pack_start(self.result, True, True, 0)

        # autofill
        completion_list = ["inverse", "sqrt", "pow", "ln", "log10"]
        store = Gtk.ListStore(str)
        for item in completion_list:
            store.append([item])
        completion = Gtk.EntryCompletion()
        completion.set_model(store)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        self.entry.set_completion(completion)

        self.connect("key-press-event", self.on_key)
    # Lisää nämä __init__-metodin loppuun (ennen self.show_all() tms.)

        # Historia-lista ja indeksi
        self.history = []               # lista edellisistä syötteistä
        self.history_index = -1         # -1 = current (ei historiassa)

        # Tallenna syöte kun painetaan Enter (tai kun haluat tallentaa)
        self.entry.connect("activate", self.on_entry_activate)

        # Napauta ylös/alas-nuolta → navigoi historiaa
        self.entry.connect("key-press-event", self.on_history_key_press)

    def on_entry_activate(self, entry):
        """Enter-painallus → tallenna syöte historiaan (jos ei tyhjä)"""
        text = entry.get_text().strip()
        if text and (not self.history or text != self.history[-1]):
            self.history.append(text)
            # Pidä lista kohtuullisen kokoisena (esim. max 50)
            if len(self.history) > 50:
                self.history.pop(0)
        self.history_index = -1         # reset navigointi

    def on_history_key_press(self, widget, event):
        """Ylös/alas-nuoli → selaa historiaa"""
        if event.keyval == Gdk.KEY_Up:
            if self.history:
                if self.history_index == -1:
                    self.current_text = widget.get_text()
                    self.history_index = len(self.history) - 1
                elif self.history_index > 0:
                    self.history_index -= 1

                widget.set_text(self.history[self.history_index])
                widget.set_position(-1)
            return True

        elif event.keyval == Gdk.KEY_Down:
            if self.history_index == -1:
                return False

            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                widget.set_text(self.history[self.history_index])
            else:
                self.history_index = -1
                if hasattr(self, 'current_text'):
                    widget.set_text(self.current_text)
                else:
                    widget.set_text("")
            widget.set_position(-1)
            return True

        return False

    def on_entry_activate(self, entry):
        """Enter-painallus → tallenna syöte historiaan"""
        text = entry.get_text().strip()
        if text and (not self.history or text != self.history[-1]):
            self.history.append(text)
            self.save_history()
            if len(self.history) > 50:
                self.history.pop(0)
        self.history_index = -1

    def save_history(self):
        """Tallenna historia history.txt-tiedostoon"""
        try:
            with open("history.txt", "w") as f:
                for item in self.history:
                    f.write(item + "\n")
        except:
            pass

    def load_history(self):
        """Lataa historia history.txt-tiedostosta"""
        try:
            with open("history.txt", "r") as f:
                self.history = [line.strip() for line in f if line.strip()]
        except:
            self.history = []
    def live_process(self, _):
        txt = self.entry.get_text()
        try:
            results = calc_expr(txt)
            out = []
            for val, part in results:
                if val == "err":
                    out.append(f"{part} → err")
                else:
                    cat = detect_category(part)
                    icon = category_icons.get(cat, "❓")
                    out.append(f"{icon} {part} →\n{format_result(val, cat)}")
            self.result.set_text("\n\n".join(out))
        except:
            self.result.set_text("err")

    def on_key(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True

win = SmartSI()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
