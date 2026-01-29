from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# =========================
# Données A320
# =========================
BEM = 42600           # Basic Empty Mass
MTOM = 77000          # Max Takeoff Mass
MLM = 66000           # Max Landing Mass
Fuel_takeoff = 6100
Trip_fuel = 3000
Taxi_fuel = 300
Traffic_load = 8000   # passagers + bagages

# Arms (m)
BEM_arm = 12.0
Traffic_arm = 15.0
Fuel_arm = 14.0

# MAC
MAC = 4.16
LEMAC = 11.0
TEMAC = LEMAC + MAC

# Enveloppe CG polygonale (CG vs masse)
CG_ENVELOPE = [
    (11.5, 40000),
    (13.0, 70000),
    (16.2, 70000),
    (15.0, 40000)
]

# =========================
# Calcul CG
# =========================
def compute_cg(masses, arms):
    total_mass = sum(masses)
    total_moment = sum(m * a for m, a in zip(masses, arms))
    return total_moment / total_mass

def cg_percent_mac(cg):
    return (cg - LEMAC) / MAC * 100

# =========================
# Route principale
# =========================
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>A320 Mass & Balance Simulator</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
body{font-family:Arial;background:#1b1b1b;color:#eee;margin:0;padding:20px;}
h1{text-align:center;color:#00ffff;margin-bottom:20px;}
.container{display:flex;gap:20px;flex-wrap:wrap;}
.panel{background:#2b2b2b;padding:20px;border-radius:10px;width:45%;box-shadow:0 0 20px #00ffff50;}
input,button{padding:8px;border-radius:5px;border:none}
input{background:#3b3b3b;color:#eee;}
button{background:#00ffff;color:#1b1b1b;font-weight:bold;cursor:pointer;width:100%;margin-top:10px;}
button:hover{background:#00bbbb;}
.range-label{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
.alert{color:#ff4444;font-weight:bold;margin-top:10px;}
.input-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
.input-row label{width:45%;text-align:left;}
.input-row input{width:50%;}
</style>
</head>
<body>
<h1>✈️ Aircraft Mass & Balance Simulator (A320 default values)</h1>
<div class="container">

  <!-- Panel Données avion + What-if -->
  <div class="panel">
    <h2>Données avion</h2>
    <div class="input-row"><label>BEM (kg)</label><input id="bem" value="42600"></div>
    <div class="input-row"><label>Traffic load (kg)</label><input id="traffic" value="8000"></div>
    <div class="input-row"><label>Fuel Takeoff (kg)</label><input id="fuel" value="6100"></div>
    <div class="input-row"><label>Trip Fuel (kg)</label><input id="trip_fuel" value="3000"></div>
    <div class="input-row"><label>Taxi Fuel (kg)</label><input id="taxi_fuel" value="300"></div>
    <div class="input-row"><label>BEM arm (m)</label><input id="bem_arm" value="12"></div>
    <div class="input-row"><label>Traffic arm (m)</label><input id="traffic_arm" value="15"></div>
    <div class="input-row"><label>Fuel arm (m)</label><input id="fuel_arm" value="14"></div>

    <h2>What-if</h2>
    <label>Masse ajoutée (kg)</label>
    <input id="added_mass" value="500">
    <div class="range-label">
      <label>Position masse ajoutée (m)</label>
      <span id="arm_value">14</span>
    </div>
    <input type="range" id="added_arm" min="1" max="30" step="0.1" value="14" oninput="calculate()">
    <button onclick="calculate()">Calculer</button>
    <div class="alert" id="alert"></div>

    <h2>Masses et MAC</h2>
    <div id="mass_mac_display">
        <p>MTOM: <span id="mtom_display">-</span> kg</p>
        <p>MLM: <span id="mlm_display">-</span> kg</p>
        <p>MZFM: <span id="mzfm_display">-</span> kg</p>
        <p>OM: <span id="om_display">-</span> kg</p>
        <p>TOM: <span id="tom_display">-</span> kg</p>
        <p>MAC: <span id="mac_display">-</span> m</p>
        <p>LEMAC: <span id="lemac_display">-</span> m</p>
        <p>TEMAC: <span id="temac_display">-</span> m</p>
    </div>

  </div>

  <!-- Panel Graphique et Gauge -->
  <div class="panel">
    <div id="results"></div>
    <div id="plot" style="height:300px;"></div>
    <div id="gauge" style="height:100px;"></div>
  </div>
</div>

<script>
function calculate(){
    arm_value.innerText = added_arm.value;
    fetch("/calculate", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            bem:bem.value,
            traffic:traffic.value,
            fuel:fuel.value,
            trip_fuel:trip_fuel.value,
            taxi_fuel:taxi_fuel.value,
            bem_arm:bem_arm.value,
            traffic_arm:traffic_arm.value,
            fuel_arm:fuel_arm.value,
            added_mass:added_mass.value,
            added_arm:added_arm.value
        })
    }).then(res=>res.json()).then(data=>{
        results.innerHTML = `
            <p>ZFM: ${data.ZFM.toFixed(0)} kg</p>
            <p>TOM: ${data.TOM.toFixed(0)} kg</p>
            <p>Ramp: ${data.Ramp.toFixed(0)} kg</p>
            <p>Landing: ${data.Landing.toFixed(0)} kg</p>
            <p><b>CG initial:</b> ${data.cg.toFixed(2)} m (${data.cg_percent.toFixed(1)}% MAC)</p>
            <p><b>CG what-if:</b> ${data.new_cg.toFixed(2)} m (${data.new_cg_percent.toFixed(1)}% MAC)</p>
        `;

        // Mettre à jour toutes les masses et MAC
        mtom_display.innerText = data.MTOM;
        mlm_display.innerText = data.MLM;
        mzfm_display.innerText = data.MZFM.toFixed(0);
        om_display.innerText = data.OM.toFixed(0);
        tom_display.innerText = data.TOM.toFixed(0);
        mac_display.innerText = data.MAC;
        lemac_display.innerText = data.LEMAC;
        temac_display.innerText = data.TEMAC;

        // Alert CG
        let cgMin=Math.min(...data.envelope.map(p=>p[0]));
        let cgMax=Math.max(...data.envelope.map(p=>p[0]));
        alert.innerText = (data.new_cg<cgMin || data.new_cg>cgMax) ? "⚠ CG hors enveloppe !" : "";

        // Graphique
        const envX=data.envelope.map(p=>p[0]).concat(data.envelope[0][0]);
        const envY=data.envelope.map(p=>p[1]).concat(data.envelope[0][1]);

        Plotly.react("plot", [
            {x:envX, y:envY, mode:"lines", name:"Enveloppe CG", line:{color:"#00ffff",width:3}},
            {x:[data.cg], y:[data.TOM], mode:"markers", name:"CG initial", marker:{size:14,color:"#00ff00"}},
            {x:[data.new_cg], y:[data.new_mass], mode:"markers", name:"CG what-if", marker:{size:14,color:"#ff4444"}}
        ], {
            xaxis:{title:"CG (m)", range:[10,17]},
            yaxis:{title:"Masse (kg)", range:[38000,78000]},
            title:"Diagramme Masse & Centrage",
            plot_bgcolor:"#1b1b1b",
            paper_bgcolor:"#2b2b2b",
            font:{color:"#eee"},
            transition:{duration:200}
        });

        Plotly.react("gauge", [{
            type:"indicator",
            mode:"gauge+number",
            value:data.new_cg,
            title:{text:"CG (m)", font:{size:18,color:"#00ffff"}},
            gauge:{
                axis:{range:[10,17]},
                bar:{color:"#ff4444"},
                steps:[
                    {range:[10,cgMin],color:"#ff4444"},
                    {range:[cgMin,cgMax],color:"#00ff00"},
                    {range:[cgMax,17],color:"#ff4444"}
                ],
                threshold:{line:{color:"yellow",width:4}, thickness:0.75, value:data.new_cg}
            }
        }], {
            height:200,
            margin:{t:0,b:0,l:0,r:0},
            plot_bgcolor:"#1b1b1b",
            paper_bgcolor:"#2b2b2b"},
        {displayModeBar:false});
    });
}
window.onload=calculate;
</script>
</body>
</html>
""")

# =========================
# Route calcul
# =========================
@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    bem = float(data["bem"])
    traffic = float(data["traffic"])
    fuel = float(data["fuel"])
    trip_fuel = float(data["trip_fuel"])
    taxi_fuel = float(data["taxi_fuel"])
    bem_arm = float(data["bem_arm"])
    traffic_arm = float(data["traffic_arm"])
    fuel_arm = float(data["fuel_arm"])
    added_mass = float(data["added_mass"])
    added_arm = float(data["added_arm"])

    # ---- Masses ----
    ZFM = bem + traffic
    TOM = ZFM + fuel
    Ramp = TOM + taxi_fuel
    Landing = TOM - trip_fuel
    OM = bem + traffic  # Operating Mass
    DOM = ZFM - Traffic_load

    # ---- CG ----
    cg = compute_cg([bem, traffic, fuel],[bem_arm, traffic_arm, fuel_arm])
    new_mass = TOM + added_mass
    new_cg = (TOM*cg + added_mass*added_arm)/new_mass

    # ---- CG % MAC ----
    cg_percent = (cg - LEMAC)/MAC*100
    new_cg_percent = (new_cg - LEMAC)/MAC*100

    return jsonify({
        "ZFM": ZFM,
        "TOM": TOM,
        "Ramp": Ramp,
        "Landing": Landing,
        "OM": OM,
        "DOM": DOM,
        "cg": cg,
        "new_mass": new_mass,
        "new_cg": new_cg,
        "cg_percent": cg_percent,
        "new_cg_percent": new_cg_percent,
        "envelope": CG_ENVELOPE,
        "MTOM": MTOM,
        "MLM": MLM,
        "MZFM": ZFM,
        "MAC": MAC,
        "LEMAC": LEMAC,
        "TEMAC": TEMAC
    })

# =========================
# Lancement serveur
# =========================
if __name__ == "__main__":
    app.run(debug=True)
