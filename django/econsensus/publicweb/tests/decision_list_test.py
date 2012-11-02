from django.core.urlresolvers import reverse

from random import randint
from string import ascii_letters, digits
from datetime import date

from decision_test_case import DecisionTestCase
from publicweb.models import Decision, Feedback
from publicweb.views import DecisionList
from lxml.html.soupparser import fromstring
from lxml.cssselect import CSSSelector


class DecisionListTest(DecisionTestCase):

    def tearDown(self):
        Decision.objects.all().delete()

    def test_all_sorts_result_in_one_arrow_present(self):
        """Assert only one sort class is present in the decision list view"""
        # Assumes CSS will be correctly displaying the sort status
        # Takes into account sort and sort-reverse
        sort_options = {'proposal': ['-id', 'excerpt', 'feedback', 'deadline', '-last_modified'],
                        'decision': ['-id', 'excerpt', 'decided_date', 'review_date'],
                        'archived': ['-id', 'excerpt', 'creation', 'archived_date']
                        }
        self.create_decisions_with_different_statuses()
        for page, sort_queries in sort_options.iteritems():
            for sort_query in sort_queries:
                response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, page]), {'sort': sort_query})
                html = fromstring(response.content)
                sort_selector = CSSSelector('table.summary-list .sort')
                sorts = sort_selector(html)
                self.assertEquals(len(sorts), 1, 'Number of sort arrows should be 1. But is ' + str(len(sorts))
                                                 + ' for page=' + page + ' sort_query=' + sort_query)

    def test_list_pages_can_be_sorted(self):
        """Test that sort works for all Decision List columns we offer it on"""
        number_of_test_decisions = 3  # Two additional empty decisions will be made

        # these are the dates we'll set in the test
        random_dates = [self._get_random_date() for i in range(number_of_test_decisions)]
        random_descriptions = [self._get_random_string(30) for i in range(number_of_test_decisions)]

        # set all the columns you want to test sorting on
        date_columns = ['deadline', 'decided_date', 'review_date', 'archived_date']

        #############################
        # Make the decisions
        #############################
        # Make an initial empty decision
        decisions = []
        decisions.append(self.make_decision(description="Decision None 1", organization=self.bettysorg))

        # Create decisions with random data
        for i in range(number_of_test_decisions):
            d = self.make_decision(description=random_descriptions[i], organization=self.bettysorg)
            for column in date_columns:
                setattr(d, column, random_dates[i])
            d.save()
            decisions.append(d)

        # Set random feedback (offset by 1 so empty decision remains empty)
        for i in range(1, number_of_test_decisions + 1):
            for f in range(randint(1, 4)):
                Feedback(description=self._get_random_string(10), decision=decisions[i], author=self.user).save()

        # Make a final empty decision
        decisions.append(self.make_decision(description="Decision None 2", organization=self.bettysorg))

        # Get the last_modified & id values
        last_modifieds = [decision.last_modified for decision in decisions]
        ids = [decision.id for decision in decisions]
        feedbackcounts = [decision.feedbackcount() for decision in decisions]
        excerpts = [decision.excerpt for decision in decisions]
        #############################

        # we need sorted values to compare against
        sorted_dates = sorted(random_dates)
        sorted_last_modifieds = sorted(last_modifieds)[::-1]  # because we sort in reverse by default
        sorted_ids = sorted(ids)[::-1]  # because we sort in reverse by default
        sorted_feedbackcounts = sorted(feedbackcounts)[::-1]  # because we sort in reverse by default
        sorted_excerpts = sorted(excerpts, key=unicode.lower)

        # Test Dates
        for column in date_columns:
            response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']), dict(sort=column))
            object_list = response.context['object_list']

            for index, sorted_date in enumerate(sorted_dates):
                self.assertEquals(sorted_date, getattr(object_list[index], column), 'Testing date sort failed for' + column)
            self.assertEquals(None, getattr(object_list[len(object_list) - 2], column), 'Testing date sort failed for' + column)
            self.assertEquals(None, getattr(object_list[len(object_list) - 1], column), 'Testing date sort failed for' + column)

        # Test Last Modified
        response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']), {'sort': '-last_modified'})
        object_list = response.context['object_list']
        for index, sorted_last_modified in enumerate(sorted_last_modifieds):
            # Replace Microsecond to enable good results on MySQL and SQLLite
            sorted_list_last_modified = sorted_last_modified.replace(microsecond=0)
            object_list_last_modified = getattr(object_list[index], 'last_modified').replace(microsecond=0)
            self.assertEquals(sorted_list_last_modified, object_list_last_modified, 'Testing date sort failed for last_modified')

        #At this point, the ids in browser are all out of order, so good time to test id sort
        response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']), {'sort': '-id'})
        object_list = response.context['object_list']
        for index, sorted_id in enumerate(sorted_ids):
            self.assertEquals(sorted_id, getattr(object_list[index], 'id'), 'Testing id sort failed')

        # Test Feedback
        response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']), {'sort': 'feedback'})
        object_list = response.context['object_list']
        for index, sorted_feedbackcount in enumerate(sorted_feedbackcounts):
            self.assertEquals(sorted_feedbackcount, object_list[index].feedbackcount(), 'Testing feedbackcount sort failed')
        self.assertEquals(0, object_list[len(object_list) - 2].feedbackcount(), 'Testing feedbackcount sort failed')
        self.assertEquals(0, object_list[len(object_list) - 1].feedbackcount(), 'Testing feedbackcount sort failed')

        # Test Excerpt
        response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']), {'sort': 'excerpt'})
        object_list = response.context['object_list']
        for index, sorted_excerpt in enumerate(sorted_excerpts):
            self.assertEquals(sorted_excerpt, getattr(object_list[index], 'excerpt'), 'Testing excerpt sort failed')

    def test_decision_list_can_be_filtered_by_status(self):
        self.create_decisions_with_different_statuses()
        response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'decision']))
        self.assertContains(response, "Issue Decision")
        self.assertNotContains(response, "Issue Proposal")
        self.assertNotContains(response, "Issue Archived")
        response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']))
        self.assertContains(response, "Last Modified")

    def test_pagination_set_paginate_by(self):
        # Test the following cases confirming both self.paginate_by and session['num'] is set
        # happy path:
        # A) if valid num in 'get' set it (and prefer it over session)
        # B) if nothing in get and something in session use session
        # C) if nothing in session or get use default
        # less happy path:
        # D) if invalid (ee or '-10') set default
        # E) if page number but no num set default (Note: this has to be a valid page so we have to use page=1 if we don't create lots of decisions)
        test_cases = [{'name': 'Test A', 'sessionnum': 25, 'querydict': {'num': 100}, 'expectednum': '100'},
                      {'name': 'Test B', 'sessionnum': 25, 'querydict': {'sort': '-id'}, 'expectednum': '25'},
                      {'name': 'Test C', 'sessionnum': None, 'querydict': {'sort': '-id'}, 'expectednum': '10'},
                      {'name': 'Test D', 'sessionnum': 25, 'querydict':  {'num': '-ee'}, 'expectednum': '10'},
                      {'name': 'Test E', 'sessionnum': 25, 'querydict':  {'page': 1}, 'expectednum': '10'}]
        for test_case in test_cases:
                # Ensure session is clean by logging out and in again
                self.client.get(reverse('auth_logout'))
                #self.login('betty') <-- TODO Don't seem to need to login??? (related to method_decorator being commented out?)
                self.assertFalse('num' in self.client.session, 'Session should be empty at start of test')

                # Set an existing session val if we need one
                if test_case['sessionnum']:
                    s = self.client.session
                    s['num'] = test_case['sessionnum']
                    s.save()
                response = self.client.get(reverse('publicweb_item_list', args=[self.bettysorg.slug, 'proposal']), test_case['querydict'])

                curr_session_num = str(self.client.session.get('num'))
                paginator_num = str(response.context['page_obj'].paginator.per_page)

                self.assertEquals(curr_session_num, test_case['expectednum'], "We did not get the expected session value for " + test_case['name'])
                self.assertEquals(paginator_num, test_case['expectednum'], "We did not get the expected paginator value for " + test_case['name'])

    def test_pagination_build_query_string(self):
        # Test the following cases confirm expected string is returned
        # A) all defaults - expect next and prev page numbers only
        # B) non-default sort - expect page numbers with sort
        # C) non-default num - expect page numbers with num
        # D) non-default sort and num - expect page numbers with num and sort
        # E) no page_obj - expect None
        # Run where prev_page = 2 & next_page = 4

        default_num = '10'
        default_sort = '-id'

        decision_list = DecisionList()
        decision_list.default_num_items = default_num

        # Set up a dummy page object
        class DummyPageObject:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        page_obj = DummyPageObject(previous_page_number=lambda: 2, next_page_number=lambda: 4)

        test_cases = [{'name': 'Test A', 'page_obj': page_obj, 'context': {'num': default_num, 'sort': default_sort}, 'expectedprev': '?page=2', 'expectednext': '?page=4'},
                      {'name': 'Test B', 'page_obj': page_obj, 'context': {'num': default_num, 'sort': 'excerpt'}, 'expectedprev': '?sort=excerpt&page=2', 'expectednext': '?sort=excerpt&page=4'},
                      {'name': 'Test C', 'page_obj': page_obj, 'context': {'num': '25', 'sort': default_sort}, 'expectedprev': '?num=25&page=2', 'expectednext': '?num=25&page=4'},
                      {'name': 'Test D', 'page_obj': page_obj, 'context': {'num': '25', 'sort': 'excerpt'}, 'expectedprev': '?sort=excerpt&num=25&page=2', 'expectednext': '?sort=excerpt&num=25&page=4'},
                      {'name': 'Test E', 'page_obj': None, 'context': {'num': '25', 'sort': 'feedback'}, 'expectedprev': None, 'expectednext': None}]

        for test_case in test_cases:
            context = test_case['context']
            context['page_obj'] = test_case['page_obj']
            returned_prev_string = decision_list.build_prev_query_string(context)
            returned_next_string = decision_list.build_next_query_string(context)
            self.assertEquals(returned_prev_string, test_case['expectedprev'], 'Did not get expected previous query')
            self.assertEquals(returned_next_string, test_case['expectednext'], 'Did not get expected next query')

    def _get_random_string(self, max_length_of_string):
        #TODO This does not generate non-english charaters
        chars = ascii_letters + digits + ' '
        return ''.join([chars[randint(0, len(chars) - 1)] for x in range(randint(1, max_length_of_string))])

    def _get_random_date(self):
        return date.fromordinal(randint(500000, 800000))
