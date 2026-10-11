import copy
from collections import Counter
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/lumi'))
from focused_data_v3 import generate, INTENTS, BANKS, SIZES
from practical_data import sha, validate_pairs, oracle, generate as v1
from practical_data_v2 import generate as v2
from run_focused_v3 import guard_pass


class FocusedV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.splits=generate()

    def test_pairs_counts_and_balanced_labels(self):
        validate_pairs(self.splits)
        for split,rows in self.splits.items():
            self.assertEqual(len(rows),SIZES[split]*4)
            for family,k in [('focused_intent',16),('focused_routing',4)]:
                counts=Counter(r['supervision']['decision']['gold'] for r in rows if r['source_family']==family and r['language']=='en')
                self.assertEqual(len(counts),k)
                self.assertEqual(set(counts.values()),{SIZES[split]//k})
        self.assertEqual(self.splits,generate())

    def test_neither_training_nor_calibration_exposes_final_intent_utterances(self):
        forbidden={item[4][lang] for item in INTENTS for lang in (0,1)}
        test_content=set()
        for split,rows in self.splits.items():
            for r in rows:
                if r['source_family']!='focused_intent':continue
                messages=[m['content'] for m in r['request']['state']]
                if split=='test':
                    self.assertIn(messages[-1],forbidden);test_content.add(messages[-1])
                else:self.assertFalse(set(messages)&forbidden)
                facts=r['provenance']['facts']
                self.assertNotEqual(facts['target'],facts['previous'])
                self.assertEqual(r['supervision']['decision']['gold'],INTENTS[facts['target']][0][0])
        self.assertEqual(test_content,forbidden)

    def test_routing_facts_and_requests_are_disjoint_from_all_previous_splits(self):
        old={sha([r['supervision']['decision']['task'],r['provenance']['facts']]) for gen in (v1,v2) for rows in gen().values() for r in rows}
        requests=set();seen=set(old)
        for rows in self.splits.values():
            for r in rows:
                self.assertNotIn(sha(r['request']),requests);requests.add(sha(r['request']))
                if r['source_family']=='focused_routing' and r['language']=='en':
                    f=r['provenance']['facts'];key=sha(['routing',f]);self.assertNotIn(key,seen);seen.add(key)
                    self.assertEqual(r['supervision']['decision']['gold'],oracle('routing',f))

    def test_wording_banks_do_not_cross_splits(self):
        ids=set()
        for split,bank in BANKS.items():
            self.assertFalse(ids&set(bank));ids.update(bank)
            self.assertEqual({r['provenance']['template_id'] for r in self.splits[split]},set(bank))

    def test_guard_rejects_loss_or_one_language_regression(self):
        base={'macro_nll':1.,'by_language':{'en':{'accuracy':.5},'it':{'accuracy':.5}}}
        cfg={'max_guard_nll_increase':.05,'max_guard_accuracy_drop':.02}
        bad=copy.deepcopy(base);bad['by_language']['it']['accuracy']=.47
        self.assertFalse(guard_pass(bad,base,cfg))
        bad=copy.deepcopy(base);bad['macro_nll']=1.06
        self.assertFalse(guard_pass(bad,base,cfg))
        self.assertTrue(guard_pass(base,base,cfg))

if __name__=='__main__':unittest.main()
