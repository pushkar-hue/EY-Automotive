# 🚗 Automotive Predictive Maintenance Agent

Welcome to the 'Automove [Hero + M&M]' hackathon project!

This repository contains the **Master Orchestrator** for our agentic AI system. Its job is to coordinate multiple "worker" agents to predict vehicle failures, talk to customers, and schedule maintenance, all while feeding insights back to manufacturing.

## 🚀 Quick Start

Get the app running on your machine in 2 minutes.

1.  **Set up a Virtual Environment** (Recommended)
    ```bash
    # Create a virtual environment
    python -m venv venv
    
    # Activate it
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows:
    venv\Scripts\activate
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Server**
    ```bash
    # This command runs the app from main.py and auto-reloads on changes
    uvicorn main:app --reload
    ```

4.  **Test It!**
    Your server is now running. Open these links in your browser:
    * **API Docs (Swagger):** `http://localhost:8000/docs`
    * **Run Full Demo:** `http://localhost:8000/demo`
        (This single link will trigger the entire test flow!)

---

## 🗺️ Project Structure

All our code is inside the `app/` directory. Here's where to find everything:

```
automotive_agent/
├── app/
│   ├── api.py           # ⭐️ All API routes (@app.get, @app.post)
│   ├── orchestrator.py  # ⭐️ The MasterAgent class (the "brain")
│   ├── schemas.py       # ⭐️ All Pydantic data models (Telematics, etc.)
│   ├── ueba.py          # ⭐️ The UEBAGuard class and security rules
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── clients.py   # ⭐️ ABSTRACT classes (the "interfaces") for agents
│   │   └── mocks.py     # ⭐️ MOCK classes (the "fake" agents we will edit)
│   │
│   ├── config.py        # App settings (e.g., USE_MOCKS)
│   └── state.py         # In-memory "databases"
│
├── main.py              # ⭐️ Runs the app with uvicorn
└── requirements.txt     # Project dependencies
```

## 🎯 Team Tasks & Where to Code

Here's the breakdown of who works where.

### 🤖 Mohit (Predictive Model)

Your goal is to make our diagnosis "smart" instead of just guessing.

* **Your File:** `app/agents/mocks.py`
* **Your Class:** `MockDiagnosisAgent`
* **Your Task:** Find the `predict` method inside this class. Right now, it just uses simple `if-else` logic.
    * **Replace this logic with your model.** You can load a `.pkl` file (e.g., from scikit-learn) or add your model code directly.
    * Your method **must** return a `PredictedIssue` object (defined in `app/schemas.py`).

### 📊 Ved (Data Analysis & Scheduling)

You're handling the "input" (data analysis) and "booking" (scheduling) parts of the flow.

* **Your File:** `app/agents/mocks.py`
* **Your Classes:**
    1.  `MockDataAgent`: Find the `analyze` method. This runs *before* Mohit's model. Your job is to add logic to find "anomalies" in the raw `Telematics` data.
    2.  `MockSchedulingAgent`: Find the `propose` and `confirm` methods. Right now, it just fakes some appointment slots. Your job is to make this smarter. (e.g., "only propose weekday slots," "check if a slot is already taken," etc.).

### 🛡️ Shiva (UEBA Guard)

You are our security and compliance layer. Your job is to spot "weird" behavior.

* **Your File:** `app/ueba.py`
* **Your Class:** `UEBAGuard`
* **Your Task:** Focus on the `log` method.
    * It already has a simple allow-list and spike detection.
    * **Improve it.** Add more heuristics. For example: "The SchedulingAgent should *never* try to read telematics data. If it does, create a **high** severity alert."
    * You can see your alerts at the `http://localhost:8000/ueba/alerts` endpoint.

### 🧠 User (Orchestrator, Voice & Feedback)

You're working on the "brain" (orchestrator) and the "voice" (customer interaction).

* **Orchestrator:**
    * **Your File:** `app/orchestrator.py`
    * **Your Class:** `MasterAgent`
    * **Your Task:** Modify the `process_telematics` method. This is the main "flow" of our entire app. If you want to change the *order* of operations (e.g., "don't call the customer if the risk is low"), this is the place to do it.

* **Voice & Feedback:**
    * **Your File:** `app/agents/mocks.py`
    * **Your Classes:** `MockVoiceAgent` and `MockFeedbackAgent`
    * **Your Task:** This is where you'll implement the actual voice/feedback logic.
        * In `MockVoiceAgent`, edit `craft_script` to make the
            conversation more persuasive.
        * In `call_owner`, you can add the `pyttsx3` and `speech_recognition` logic we discussed to replace the `random.random() < 0.8` (just make sure to `pip install` them!).
        * In `MockFeedbackAgent`, improve the `request_feedback` method.

---

## 🤝 How We Work (IMPORTANT!)

1.  **All Agents are MOCKED:** We are *not* building 6 different microservices. We are all editing the "mock" implementations in `app/agents/mocks.py`.
2.  **The Schema is LAW:** If you need to pass new data between agents, you **must** add it to a Pydantic model in `app/schemas.py`. This prevents our app from breaking.
3.  **Test with the Demo Endpoint:** After you make a change, save the file (uvicorn will auto-reload) and just refresh `http://localhost:8000/demo` in your browser to run a full test.
