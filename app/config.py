# set to False to call real worker services over HTTP
USE_MOCKS = True 

# For real HTTP workers, define base URLs like:
WORKER_URLS = {
    "data": "http://data-agent:7001",
    "diagnosis": "http://diagnosis-agent:7002",
    "voice": "http://voice-agent:7003",
    "scheduling": "http://scheduling-agent:7004",
    "feedback": "http://feedback-agent:7005",
    "mfg": "http://mfg-agent:7006",
}