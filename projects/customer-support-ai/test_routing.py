import unittest
from unittest.mock import patch
from api import answer_request

CONTEXT={"purchase_date":"2026-10-25","country":"US","category":"footwear"}

def classified(topic, aspect="none", second=None):
    requests=[{"topic":topic,"aspect":aspect}]
    if second:
        requests.append(second)
    return {"requests":requests}

class RoutingTests(unittest.TestCase):
    def ask(self, question, topic, aspect="none", context=CONTEXT):
        return answer_request({"question":question,"context":context},
            classifier=lambda _: classified(topic, aspect))

    def test_return_duration_routes_to_window(self):
        result=self.ask("How many days to send them back?","return_policy","window")
        self.assertEqual(result['sources'][0]['passage_id'],'returns-v1-window')

    def test_return_condition_routes_to_condition(self):
        result=self.ask("Can I return these after wearing?","return_policy","condition")
        self.assertEqual(result['sources'][0]['passage_id'],'returns-v1-condition')

    def test_duration_not_calendar_deadline(self):
        result=self.ask("What is the time limit to return these?","return_policy","window")
        self.assertEqual(result['status'],'answered')

    def test_calendar_deadline_remains_separate(self):
        result=self.ask("What is my last day to return these?","return_policy","deadline")
        self.assertEqual(result['status'],'clarify')

    def test_classifier_window_cannot_hide_explicit_final_date_request(self):
        result=self.ask("Please work out the final day I can initiate a return.","return_policy","window")
        self.assertEqual(result['status'],'clarify')
        self.assertIn('Exact deadline calculation is not implemented',result['answer'])

    def test_dates_still_select_version(self):
        result=self.ask("How much time do I have to return these?","return_policy","window",
            dict(CONTEXT,purchase_date='2026-11-01'))
        self.assertEqual(result['policy_version'],'v2')

    def test_missing_context_remains_required(self):
        result=self.ask("How much time do I have to return these?","return_policy","window",{})
        self.assertEqual(result['status'],'clarify')

    def test_invalid_classifier_output_stops_safely(self):
        result=answer_request({'question':'return window','context':CONTEXT},
            classifier=lambda _: {'intent':'invented'})
        self.assertEqual(result['status'],'clarify')
        self.assertEqual(result['sources'],[])

    def test_unsupported_stops_before_retrieval_and_generation(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'How long will the battery last?','context':CONTEXT},
                generator=lambda _: self.fail('generator must not run'),
                classifier=lambda _: classified('unsupported'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'insufficient_evidence')
        self.assertEqual(result['sources'],[])
        self.assertEqual(result['generation'],'disabled')

    def test_ambiguous_stops_before_retrieval_and_generation(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'Help me','context':CONTEXT},
                generator=lambda _: self.fail('generator must not run'),
                classifier=lambda _: classified('clarify'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_multiple_requests_stop_before_retrieval_and_generation(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'Return this and track my parcel','context':CONTEXT},
                generator=lambda _: self.fail('generator must not run'),
                classifier=lambda _: classified('return_policy','window',
                    {"topic":"order_status","aspect":"none"}))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_repair_question_cannot_enter_return_retrieval(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'Can I replace the heel taps?','context':CONTEXT},
                classifier=lambda _: classified('return_policy','exception'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_discount_question_cannot_enter_return_retrieval(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'Can I get a discount on another pair?','context':CONTEXT},
                classifier=lambda _: classified('return_policy','refund_guarantee'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_arrival_defect_policy_question_can_reach_policy_retrieval(self):
        result=answer_request({'question':'The package arrived damaged. Does the policy cover this?','context':CONTEXT},
            classifier=lambda _: classified('return_policy','exception'))
        self.assertEqual(result['status'],'insufficient_evidence')
        self.assertIn('does not specify',result['answer'])

    def test_arrival_defect_with_implicit_return_policy_cue_is_rescued(self):
        result=answer_request({'question':'This pair arrived with a torn seam. What exception does the policy allow?','context':CONTEXT},
            classifier=lambda _: {"requests":[{"topic":"clarify","aspect":"none"},{"topic":"unsupported","aspect":"none"}]})
        self.assertEqual(result['status'],'insufficient_evidence')
        self.assertIn('does not specify',result['answer'])

    def test_missing_box_is_condition_not_unknown_defect(self):
        result=answer_request({'question':'The box was discarded. Can I still return the shoes?','context':CONTEXT},
            classifier=lambda _: classified('return_policy','exception'))
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['sources'][0]['passage_id'],'returns-v1-condition')

    def test_repair_question_without_policy_cue_still_stops(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'The heel taps need replacing. What should I do?','context':CONTEXT},
                classifier=lambda _: classified('return_policy','exception'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_mixed_product_and_return_stops_even_if_model_picks_one(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'Tell me if these are leather and whether I can return them.','context':CONTEXT},
                classifier=lambda _: classified('return_policy','condition'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_order_word_alone_does_not_trigger_tracking_route(self):
        with patch('api.respond') as retrieve:
            result=answer_request({'question':'I have an issue with my order.','context':CONTEXT},
                classifier=lambda _: classified('order_status'))
        retrieve.assert_not_called()
        self.assertEqual(result['status'],'clarify')

    def test_classifier_is_called_once(self):
        calls=[]
        def classifier(_):
            calls.append(True)
            return classified('unsupported')
        answer_request({'question':'How long will the battery last?','context':CONTEXT},classifier=classifier)
        self.assertEqual(len(calls),1)

    def test_order_status_is_bounded_but_tool_unavailable(self):
        result=self.ask('Locate my parcel','order_status')
        self.assertEqual(result['status'],'unavailable')

if __name__=='__main__': unittest.main()
