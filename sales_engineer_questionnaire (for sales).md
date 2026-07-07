# Sales Engineer Discovery Questionnaire (Pipeline Complete)

Use this script during discovery/technical qualification calls to collect everything needed to populate the VBU Intelligence pipeline end-to-end.

## 1) Call And Account Context

1. What is the exact account/client name as it should appear in the report?
2. What date range should we include for analyzed calls/transcripts?
3. Which specific calls should be included in the analysis (titles/dates/participants)?
4. Who attended this call (name, title, role in deal)?

## 2) Core Modernization Inputs (Required)

1. What is your primary legacy/source technology stack today? (VB6, VB.NET, Access, PowerBuilder, WebForms, WinForms, Clarion, Silverlight, ASP Classic, Informix, Delphi, other)
2. What is your target platform/target architecture? (example: .NET 8 on Azure)
3. Approximately how many total lines of code are in scope for modernization?
4. How would you rate current code complexity? (Clean, Conventional, Complex, Spaghetti)
5. How many customer-side developers are currently assigned to modernization?
6. In one or two sentences, how would you summarize the current state and migration goal?

## 3) Hosting & Reliability Needs
*(Engineering translation: Architecture And Hosting Decision — Estimator)*

1. Where does the customer want their data/database to live — fully in the cloud, kept on their own servers, or a mix of both? *(maps to: Azure / on-premises / hybrid)*
2. Is there a specific city, country, or region where the customer needs their systems hosted, for legal, performance, or preference reasons? If they have no preference, we'll default to East US. *(maps to: Azure region)*
3. How much downtime, if any, can the customer tolerate? Do they need the system running and available around the clock, or is standard business-hours reliability good enough? *(maps to: availability/SLA expectations)*
4. Are there any legal, regulatory, or internal policy rules about where the customer's data must physically be stored (for example, data must stay in-country, or industry rules like healthcare or financial compliance)? *(maps to: data residency/compliance constraints)*

## 4) Application Hosting Capacity
*(Engineering translation: App Service Inputs)*

1. How much computing "horsepower" does the customer expect their application to need day-to-day — would you describe their usage as light, moderate, or heavy? *(maps to: App Service plan SKU)*
2. Roughly how many copies of the application should be running at the same time to comfortably handle normal, everyday traffic? *(maps to: App Service instance count)*
3. Does the customer expect busy periods — like month-end, seasonal spikes, big promotions, or product launches — where traffic increases a lot? If so, when and how much? *(maps to: peak traffic sizing)*

## 5) Real-Time / Live Update Needs
*(Engineering translation: SignalR Inputs)*

1. Does the customer's application need real-time features, like live notifications, chat, or dashboards that update instantly without refreshing? How business-critical is that feature — nice-to-have, standard, or mission-critical? *(maps to: SignalR tier)*
2. Roughly how many users would be using those real-time features at the same time when the system first launches? *(maps to: SignalR units)*
3. On a typical day, about how many people do we expect to be connected to the system at once? *(maps to: concurrent user/connection profile)*

## 6) Database Needs (Ask Based On Where Their Data Lives)

### If Fully Cloud-Hosted Database

1. Will the customer's database live entirely in the cloud for this estimate? (yes/no) *(maps to: Azure SQL enabled)*
2. How demanding is the database workload — would you call it light, moderate, or heavy? *(maps to: Azure SQL tier/vCore size)*
3. Roughly how much data (in GB) does the customer expect to store when they first go live? *(maps to: SQL storage)*
4. Should the database run at a fixed, always-on size, or would the customer prefer something that automatically scales up and down (and can pause) based on usage? *(maps to: Provisioned vs. Serverless compute model)*

### If On-Site or Mixed (Hybrid) Database

1. Does the customer need their cloud system to connect back to servers they keep on-site? (yes/no) *(maps to: hybrid/on-prem connectivity enabled)*
2. How much traffic and reliability does that on-site connection need to support — basic, standard, or high-performance? *(maps to: VPN Gateway tier)*
3. Roughly how much data do they expect to send from the cloud back to their own servers each month (in GB)? *(maps to: outbound egress to on-prem)*
4. Do they need standard-level or premium-level security for storing sensitive passwords, keys, and credentials? *(maps to: Key Vault tier)*
5. Roughly how often will the system need to access those stored credentials — rarely, occasionally, or frequently? *(maps to: Key Vault secret operations volume)*

## 7) Monitoring & Visibility Needs
*(Engineering translation: Monitoring Inputs)*

1. Does the customer just want basic health/uptime monitoring, or do they want deeper analytics and insights into how the system is performing? *(maps to: Azure Monitor/App Insights tier)*
2. Roughly how much activity or log data do you expect the system to generate each month — a little, a moderate amount, or a lot? *(maps to: monthly log ingestion volume)*
3. Are there any requirements to keep historical monitoring data for a long time, for example for audits or compliance reviews? *(maps to: retention/observability requirements)*

## 8) DIY Cost Comparison Inputs
*(Engineering translation: Cost Dashboard Assumptions)*

1. If the customer tried to build and maintain this themselves instead of using us, how many engineers do you think they'd need to dedicate to it? *(maps to: DIY engineer count)*
2. What would be the fully-loaded annual cost per engineer for this customer — salary plus benefits and overhead? If they're not sure, we can use an industry-standard estimate. *(maps to: annual fully loaded cost per engineer)*
3. Would it help the customer to see a range — best case, likely case, and worst case — for staffing and cost, rather than a single number? *(maps to: sensitivity ranges)*

## 9) Sales Strategy And Qualification Inputs

1. What is the business impact if this legacy system fails or is delayed? (dollars/hour or business KPI impact)
2. How urgent is the migration timeline? (Immediate, This quarter, This year, No fixed date)
3. What is driving the deal most? (risk reduction, speed, cost, compliance, innovation)
4. Who is the economic buyer and who signs the final approval?
5. Who is the technical champion and day-to-day owner?
6. What internal blockers do you expect? (procurement, security review, architecture review, resourcing, change resistance)
7. Which objections are most likely from stakeholders?
8. Have you attempted modernization before? If yes, what stalled it?
9. What does success look like in 6-12 months?
10. What concrete next step can we commit to now? (deep dive, pilot scope, SOW draft, exec review)
11. What timeline should we target for pilot approval and full project start?

## 10) Evidence Capture Prompts (For Transcript-Backed Strategy)

1. Can you share direct quotes that indicate urgency?
2. Can you share direct quotes that describe risk and complexity?
3. Can you share direct quotes that reveal buyer persona and decision dynamics?
4. Can you share direct quotes that support ROI/value messaging?

## 11) Completion Checklist (Before Ending Call)

- Source technology captured
- Target platform captured
- Lines of code captured
- Complexity level captured
- Customer dev count captured
- DB mode selected (Azure SQL or On-Prem)
- Estimator sizing captured (App, SignalR, DB/Hybrid, Monitor)
- DIY staffing/cost assumptions captured
- Buyer/champion/blockers/urgency captured
- Next action and timeline agreed

## Field Mapping (Questionnaire -> Pipeline)

- state.clientName <- Section 1
- state.extracted.sourceTech <- Section 2
- state.extracted.targetTech <- Section 2
- state.extracted.linesOfCode <- Section 2
- state.extracted.complexityLevel <- Section 2
- state.extracted.customersDevCount <- Section 2
- state.extracted.summary <- Section 2
- state.blazorEstimatorPrefill.dbMode <- Section 3
- state.blazorEstimatorPrefill.region <- Section 3
- state.blazorEstimatorPrefill.app.sku <- Section 4
- state.blazorEstimatorPrefill.app.instances <- Section 4
- state.blazorEstimatorPrefill.signalr.tier <- Section 5
- state.blazorEstimatorPrefill.signalr.units <- Section 5
- state.blazorEstimatorPrefill.azureSql.* <- Section 6 (Azure SQL)
- state.blazorEstimatorPrefill.onPrem.* <- Section 6 (On-Prem/Hybrid)
- state.blazorEstimatorPrefill.monitor.* <- Section 7
- state.engineerCount/state.engineerCost <- Section 8
- state.salesStrategy/state.salesEvidence <- Sections 9 and 10
