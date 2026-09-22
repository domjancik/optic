import unittest
import engine

class NumericValidationTests(unittest.TestCase):
    def test_invalid_counts_report_the_field_instead_of_type_errors(self):
        for field in ('rays','resolution','max_bounces','seed'):
            for value in ('512',None,True,1.5,float('nan')):
                with self.subTest(field=field,value=value):
                    cfg=engine.defaults();cfg[field]=value
                    with self.assertRaisesRegex(ValueError,field+' must be a finite integer'):
                        engine.validate(cfg)
