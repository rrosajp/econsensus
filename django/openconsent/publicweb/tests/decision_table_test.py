from publicweb.decision_table import DecisionTable
from publicweb.models import Decision
from publicweb.tests.decision_test_case import DecisionTestCase

class DecisionTableTest(DecisionTestCase):
    
    def test_table_has_actvity_column(self):
        table = DecisionTable(Decision.objects.all())
        
        self.assertTrue("unresolvedfeedback" in table.columns.names())

