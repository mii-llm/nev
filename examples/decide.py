"""Minimal local inference example; no implicit download or published repository ID."""
import argparse
import json
from decision_model import DecisionModel

p=argparse.ArgumentParser()
p.add_argument('--model',required=True)
p.add_argument('--language',choices=['en','it'],default='en')
p.add_argument('--device',default=None)
a=p.parse_args()
italian=a.language=='it'
m=DecisionModel.from_pretrained(a.model,device=a.device)
result=m.evaluate(
    state='Il pacco non è arrivato. Vorrei sapere dove si trova.' if italian else 'My parcel has not arrived. I want to know where it is.',
    questions={'route':{'type':'choice',
        'instructions':'Scegli il reparto che deve gestire la richiesta.' if italian else 'Choose the department that should handle this request.',
        'criteria':{'shipping':'Spedizioni e consegne' if italian else 'Shipping and delivery',
                    'billing':'Pagamenti e fatture' if italian else 'Payments and invoices',
                    'account':'Accesso e profilo' if italian else 'Login and profile'}}})
print(json.dumps(result,ensure_ascii=False,indent=2))
