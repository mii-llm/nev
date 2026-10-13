"""Run a runtime-selected toolset. The engine receives no evaluation case or gold plan."""
import argparse
import json
from pathlib import Path
from backend import Backend
from fixtures import FixtureExecutor
from runtime import ARMS,GenericAgent,render


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--toolsets',type=Path,default=Path(__file__).with_name('toolsets.json'))
    p.add_argument('--toolset',required=True);p.add_argument('--message',required=True)
    p.add_argument('--language',choices=['en','it'],default='en');p.add_argument('--arm',choices=ARMS,default='nev_ranked')
    a=p.parse_args();kit=json.loads(a.toolsets.read_text())[a.toolset]
    result=GenericAgent(Backend()).run(a.message,a.language,kit['schemas'][a.language],FixtureExecutor(kit['responses']),a.arm,7100)
    result.update(request=a.message,language=a.language);print(render(result))

if __name__=='__main__':main()
