# From a Rhine Signal to Action: Manufacturing in the BioValley

**Use real Rhine-region data to keep critical biopharma materials moving.**

**Track:** High-tech manufacturing

Build a smart manufacturing cell that turns real public data about Rhine conditions, Basel traffic, and weather into physical decisions on the factory floor: prioritize, buffer, reroute, or quarantine critical material.

## The challenge

Basel is one of Europe's major life-sciences manufacturing regions. Modern pharmaceutical and biotech production depends not only on what happens inside a factory, but also on what is happening around it.

A change in Rhine conditions can affect logistics. Heavy road traffic can delay deliveries. Extreme weather can increase transportation and cold-chain risk.

**What if a factory could see these disruptions developing and change its material-flow decisions before production is affected?**

Build a manufacturing control system that turns real-world open data into actionable factory decisions.

## The manufacturing scenario

Imagine a Basel-area biopharmaceutical manufacturing facility. The factory depends on a critical refrigerated biopharma reagent or intermediate used during production. For this challenge, assume that the material:

- requires refrigerated handling at **2–8 °C**;
- is critical to an upcoming manufacturing step;
- should spend as little unnecessary time as possible outside controlled storage;
- may require quality review if its handling conditions are uncertain; and
- cannot be replaced instantly if the next delivery is disrupted.

The factory therefore needs to continuously decide what should happen to critical material already in its network.

### Possible actions

- **Expedite:** Prioritize the material and move it toward the required production step.
- **Buffer:** Keep the material safely in controlled storage until it is required.
- **Reroute:** Recommend another logistics route, receiving point, or manufacturing path because the expected route is at risk.
- **Quarantine:** Flag the material for quality review when conditions indicate that its handling may have been compromised.

The system should explain why it made its decision.

## Mission

Build a working application that combines at least **two real open-data sources** and converts them into a manufacturing risk or priority decision.

**Open Data → Disturbance Detection → Risk Assessment → Manufacturing Decision → Factory Dashboard**

The solution can be as simple or sophisticated as the team chooses.

## Real-world disturbances

### Rhine conditions

Use real measurements of Rhine water level and discharge around Basel. Abnormal water conditions can create logistics risk for material transported through the Rhine corridor. The system might detect:

- rapidly rising water levels;
- high-water conditions;
- unusually low water conditions;
- significant changes in discharge; or
- trends indicating deteriorating conditions.

Translate river measurements into an operational question: **Could replenishment of a critical production material become less reliable?**

### Basel road traffic

Use Basel's real traffic-counting data to identify congestion or unusually high traffic around important logistics corridors. Possible signals include:

- increased vehicle counts;
- increased heavy-vehicle traffic;
- unusual congestion periods; or
- differences between normal and abnormal traffic patterns.

The application could use this information to recommend **Normal → Buffer → Expedite → Reroute**.

### Weather

Use MeteoSwiss measurements such as temperature, precipitation, wind, humidity, or radiation. Weather can affect transportation reliability and the handling risk of refrigerated materials. For example, high temperature combined with traffic disruption and a critical production deadline could produce a higher risk score than any one signal alone.

## What to build

### Open-data integration

Connect to or import at least two provided open datasets. Teams may use current data or replay a real historical period, allowing the demo to show a meaningful disruption even if conditions during the hackathon are normal.

### Disturbance detection

Determine when conditions become unusual or operationally important. Possible methods include thresholds, historical comparisons, anomaly detection, forecasting, machine learning, optimization, or combinations of signals.

### Manufacturing risk score

Convert external conditions into information a factory operator can understand.

### Visual interface

Show the decision in a way a manufacturing operator could understand quickly. Possible formats include a control-room dashboard, a map of Basel and the Rhine, a digital factory floor, a supply-chain digital twin, a material-flow visualization, or an alerting interface.
