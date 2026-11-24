"""Local META145C CLI. Never starts background work, host posting, or API requests."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .core import build
from .viewer import render_viewer

def main():
 p=argparse.ArgumentParser(description='Offline source-bound Atlas 144+1 glyph/cymatic memory build')
 p.add_argument('--ariadne',required=True,help='Authorized original Ariadne v0.7 atlas.json')
 p.add_argument('--openalex',required=True,help='Pinned frozen 4516-topic original CSV')
 p.add_argument('--output',required=True,help='Local private artifact directory')
 p.add_argument('--samples',type=int,default=31)
 a=p.parse_args();m=build(a.ariadne,a.openalex,a.output,a.samples)
 view=render_viewer(Path(a.output)/'atlas_meta145_knowledge.sqlite',Path(a.output)/'META145_GLYPH_SYNTHESIS.json',Path(a.output)/'sphere144_reviews.json',Path(a.output)/'META145C_INTERACTIVE_OBSERVATORY.html')
 print(json.dumps({'build':'META145C','status':'LOCAL_ONLY_TESTED_CANDIDATE','meta_sha':m['meta_receipt_sha256'],'viewer':view,'performance':m['performance'],'rights':'NOT_AUTHENTICATED','canon':'UNCHANGED'},indent=2))
if __name__=='__main__':main()
