"""Frozen promotion evaluation set for the experimental request classifier."""
import argparse,json,time
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler

CTX={"purchase_date":"2026-10-25","delivery_date":"2026-11-03","country":"US","category":"footwear"}
ROWS=[
 # 15 unsupported product or adjacent topics
 ("u01","Is the tongue padded?","unsupported","none","insufficient_evidence","unsupported"),
 ("u02","Are these vegan materials?","unsupported","none","insufficient_evidence","unsupported"),
 ("u03","Can I replace the heel taps?","unsupported","none","insufficient_evidence","unsupported"),
 ("u04","Do these come in half sizes?","unsupported","none","insufficient_evidence","unsupported"),
 ("u05","Are they suitable for a kitchen with oily floors?","unsupported","none","insufficient_evidence","unsupported"),
 ("u06","What is the weight of one shoe?","unsupported","none","insufficient_evidence","unsupported"),
 ("u07","Can I use them for tennis?","unsupported","none","insufficient_evidence","unsupported"),
 ("u08","What kind of leather is used?","unsupported","none","insufficient_evidence","unsupported"),
 ("u09","Are replacement insoles available?","unsupported","none","insufficient_evidence","unsupported"),
 ("u10","Will the color fade in sunlight?","unsupported","none","insufficient_evidence","unsupported"),
 ("u11","Do they have a steel shank?","unsupported","none","insufficient_evidence","unsupported"),
 ("u12","How do I protect the suede from stains?","unsupported","none","insufficient_evidence","unsupported"),
 ("u13","Would these work for a marathon?","unsupported","none","insufficient_evidence","unsupported"),
 ("u14","Are they slip-resistant on wet stairs?","unsupported","none","insufficient_evidence","unsupported"),
 ("u15","Can I get a discount on a second pair?","unsupported","none","insufficient_evidence","unsupported"),
 # 15 supported single requests
 ("s01","How many days after delivery can I start a return?","return_policy","window","answered","supported"),
 ("s02","What is the allowed return period?","return_policy","window","answered","supported"),
 ("s03","Can I return shoes tried only on carpet?","return_policy","condition","answered","supported"),
 ("s04","I wore these outdoors. Does that affect whether I can return them?","return_policy","condition","answered","supported"),
 ("s05","The zipper was broken when the package arrived. What exception applies?","return_policy","exception","insufficient_evidence","supported"),
 ("s06","The package came damaged. Does the policy cover this?","return_policy","exception","insufficient_evidence","supported"),
 ("s07","What is my final date to request a return?","return_policy","deadline","clarify","supported"),
 ("s08","Calculate the last calendar day for my return.","return_policy","deadline","clarify","supported"),
 ("s09","Can anyone promise that my refund will be approved?","return_policy","refund_guarantee","unsupported","supported"),
 ("s10","Where is the package I ordered?","order_status","none","unavailable","supported"),
 ("s11","Has my shipment been delivered yet?","order_status","none","unavailable","supported"),
 ("s12","Can I send the shoes back if the original wrapping is gone?","return_policy","condition","answered","supported"),
 ("s13","How long do I have to change my mind about the purchase?","return_policy","window","answered","supported"),
 ("s14","My pair arrived with a tear in the upper. What return exception is there?","return_policy","exception","insufficient_evidence","supported"),
 ("s15","Will you guarantee I get my money back?","return_policy","refund_guarantee","unsupported","supported"),
 # 10 multi-intent requests: must not be answered as a single request
 ("m01","Can I return these and where is my delivery?","clarify","none","clarify","mixed"),
 ("m02","Are they waterproof, and what is the return window?","clarify","none","clarify","mixed"),
 ("m03","Change my address and tell me how long returns take.","clarify","none","clarify","mixed"),
 ("m04","How do they fit, and can I get a refund?","clarify","none","clarify","mixed"),
 ("m05","Track the parcel and tell me whether worn shoes are returnable.","clarify","none","clarify","mixed"),
 ("m06","What material are these made from? Also, how many days to return?","clarify","none","clarify","mixed"),
 ("m07","Do these have arch support, and have they shipped?","clarify","none","clarify","mixed"),
 ("m08","I need a refund and want to change the delivery address.","clarify","none","clarify","mixed"),
 ("m09","Are they good for running? Can I send them back if I try them?","clarify","none","clarify","mixed"),
 ("m10","Tell me the exact return date and check my order status.","clarify","none","clarify","mixed"),
 # 10 ambiguous or unsupported non-product queries
 ("a01","Can you help with this purchase?","clarify","none","clarify","ambiguous"),
 ("a02","What should I do now?","clarify","none","clarify","ambiguous"),
 ("a03","I have a question about my shoes.","clarify","none","clarify","ambiguous"),
 ("a04","Tell me about this item.","clarify","none","clarify","ambiguous"),
 ("a05","Is it okay?","clarify","none","clarify","ambiguous"),
 ("a06","What is your store's phone number?","unsupported","none","insufficient_evidence","ambiguous"),
 ("a07","Do you sell shoe polish?","unsupported","none","insufficient_evidence","ambiguous"),
 ("a08","When does your shop close today?","unsupported","none","insufficient_evidence","ambiguous"),
 ("a09","Can I speak to a person about my purchase?","unsupported","none","insufficient_evidence","ambiguous"),
 ("a10","Do you have a store near me?","unsupported","none","insufficient_evidence","ambiguous"),
]
CASES=[{"id":i,"question":q,"topic":t,"aspect":a,"status":s,"group":g} for i,q,t,a,s,g in ROWS]

def run(port):
 opener=build_opener(ProxyHandler({}));results=[]
 for c in CASES:
  req=Request(f"http://127.0.0.1:{port}/api/answer",data=json.dumps({"question":c["question"],"context":CTX}).encode(),headers={"Content-Type":"application/json"},method="POST");start=time.monotonic()
  with opener.open(req,timeout=60) as resp:r=json.load(resp)
  route=r.get("routing",{});checks={"topic":route.get("topic")==c["topic"],"aspect":route.get("aspect")==c["aspect"],"status":r.get("status")==c["status"]}
  if r.get("status")=="answered" and r.get("sources"):checks["citation"]=bool(r["sources"][0].get("passage_id"))
  results.append({"id":c["id"],"group":c["group"],"question":c["question"],"expected":{"topic":c["topic"],"aspect":c["aspect"],"status":c["status"]},"actual":{"topic":route.get("topic",route.get("status")),"aspect":route.get("aspect"),"status":r.get("status")},"checks":checks,"passed":all(checks.values()),"answer":r.get("answer"),"seconds":round(time.monotonic()-start,3)})
 grouped={g:[x for x in results if x["group"]==g] for g in ("unsupported","supported","mixed","ambiguous")}
 return {"kind":"frozen 50-case exploratory promotion evaluation","limitations":"Developer-authored fixed set, one run, local small model; passing does not establish production reliability.","case_count":len(results),"all_passed":sum(x["passed"] for x in results),"unsupported_false_accepts":sum(x["actual"]["topic"]=="return_policy" for x in grouped["unsupported"]),"unsupported_cases":len(grouped["unsupported"]),"mixed_answered":sum(x["actual"]["status"]=="answered" for x in grouped["mixed"]),"mixed_cases":len(grouped["mixed"]),"supported_correct":sum(x["passed"] for x in grouped["supported"]),"supported_cases":len(grouped["supported"]),"supported_clarified":sum(x["actual"]["status"]=="clarify" for x in grouped["supported"]),"results":results}

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--port",type=int,required=True);p.add_argument("--output",default="promotion-results.json");a=p.parse_args();d=run(a.port);Path(a.output).write_text(json.dumps(d,indent=2)+"\n");print(json.dumps({k:v for k,v in d.items() if k!="results"},indent=2))
