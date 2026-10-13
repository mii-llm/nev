"""Mock executor only: no access to expected plans, case labels, or answer anchors."""
import copy


class FixtureExecutor:
    def __init__(self,responses):self.responses=responses
    def __call__(self,call):
        for item in self.responses:
            if call==item['call']:return copy.deepcopy(item['result'])
        return {'error':'not_found'}
