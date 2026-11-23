import json, hashlib, statistics, time
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
CTX={"purchase_date":"2026-10-25","delivery_date":"2026-11-03","country":"US","category":"footwear"}
here=Path(__file__).parent
case_path=here/"holdout-v10-cases.json"
case_bytes=case_path.read_bytes()
cases=json.loads(case_bytes)
def run(port):
    opener=build_opener(ProxyHandler({})); rows=[]
    for c in cases:
        payload={"question":c["question"],"context":CTX}
        req=Request(f"http://127.0.0.1:{port}/api/answer",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
        start=time.monotonic()
        with opener.open(req,timeout=90) as response: result=json.load(response)
        route=result.get("routing",{})
        actual={"topic":route.get("topic",route.get("status")),"aspect":route.get("aspect"),"status":result.get("status")}
        exp={k:c[k] for k in ("topic","aspect","status")}
        rows.append({"id":c["id"],"group":c["group"],"question":c["question"],"expected":exp,"actual":actual,"passed":actual==exp,"answer":result.get("answer"),"seconds":round(time.monotonic()-start,3)})
    groups={g:[x for x in rows if x["group"]==g] for g in ("unsupported","supported","mixed","ambiguous")}
    answerable=[x for x in groups["supported"] if x["expected"]["status"]!="clarify"]
    total=sum(x["passed"] for x in rows)
    return {"kind":"fresh frozen 50-question wording evaluation; one local-model run","evaluation_set_sha256":hashlib.sha256(case_bytes).hexdigest(),"code_unchanged_during_run":True,"cases":len(rows),"exact_outcomes":total,"exact_match_rate":round(total/len(rows),3),"unsupported_return_routes":sum(x["actual"]["topic"]=="return_policy" for x in groups["unsupported"]),"unsupported_cases":len(groups["unsupported"]),"mixed_requests_answered":sum(x["actual"]["status"]=="answered" for x in groups["mixed"]),"mixed_cases":len(groups["mixed"]),"supported_correct":sum(x["passed"] for x in groups["supported"]),"supported_cases":len(groups["supported"]),"unnecessary_clarifications":sum(x["actual"]["status"]=="clarify" for x in answerable),"answerable_supported_cases":len(answerable),"ambiguous_clarified":sum(x["actual"]["status"]=="clarify" for x in groups["ambiguous"]),"mean_latency_seconds":round(statistics.mean(x["seconds"] for x in rows),3),"median_latency_seconds":round(statistics.median(x["seconds"] for x in rows),3),"limitations":"Developer-authored evaluation, one local model and one run; not evidence of production reliability.","results":rows}
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--port",type=int,required=True);p.add_argument("--output",default="holdout-v10-results.json");a=p.parse_args()
    data=run(a.port);Path(a.output).write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps({k:v for k,v in data.items() if k!="results"},indent=2))

