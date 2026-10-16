from backend.coverage.logic import result_for,summarize

def test_detected():assert result_for(True,True)[0]=='detected'
def test_not_detected():assert result_for(True,False)[0]=='not_detected'
def test_inconclusive():assert result_for(False,True)[0]=='inconclusive'
def test_empty():assert summarize([])['observed_detection_rate_percent'] is None
def test_rate():assert summarize(['detected','not_detected','inconclusive'])['observed_detection_rate_percent']==50.0
