import unittest
from unittest.mock import MagicMock
import xml.etree.ElementTree as ET
from lib.xbrl_parser import FinancialDataExtractor, XBRL_NAMESPACES


class TestConsolidatedDetection(unittest.TestCase):
    """Test cases for consolidated vs non-consolidated data detection"""
    
    def setUp(self):
        self.extractor = FinancialDataExtractor()
    
    def test_consolidated_member_detection(self):
        """Test detection of ConsolidatedMember in context elements"""
        xbrl_with_consolidated = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:xbrli="http://www.xbrl.org/2003/instance"
              xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
              xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-08-31/jppfs_cor">
            <xbrli:context id="CurrentYearInstant">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">EDI001</xbrli:identifier>
                    <xbrli:segment>
                        <xbrldi:explicitMember dimension="jppfs_cor:ConsolidatedOrNonConsolidatedAxis">
                            jppfs_cor:ConsolidatedMember
                        </xbrldi:explicitMember>
                    </xbrli:segment>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:instant>2025-03-31</xbrli:instant>
                </xbrli:period>
            </xbrli:context>
        </xbrl>"""
        
        root = ET.fromstring(xbrl_with_consolidated)
        self.assertTrue(self.extractor._has_consolidated_data(root))
    
    def test_non_consolidated_member_detection(self):
        """Test that NonConsolidatedMember alone doesn't indicate consolidated data"""
        xbrl_without_consolidated = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:xbrli="http://www.xbrl.org/2003/instance"
              xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
              xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-08-31/jppfs_cor">
            <xbrli:context id="CurrentYearInstant">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">EDI001</xbrli:identifier>
                    <xbrli:segment>
                        <xbrldi:explicitMember dimension="jppfs_cor:ConsolidatedOrNonConsolidatedAxis">
                            jppfs_cor:NonConsolidatedMember
                        </xbrldi:explicitMember>
                    </xbrli:segment>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:instant>2025-03-31</xbrli:instant>
                </xbrli:period>
            </xbrli:context>
        </xbrl>"""
        
        root = ET.fromstring(xbrl_without_consolidated)
        self.assertFalse(self.extractor._has_consolidated_data(root))
    
    def test_mixed_contexts(self):
        """Test when both ConsolidatedMember and NonConsolidatedMember exist"""
        xbrl_mixed = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:xbrli="http://www.xbrl.org/2003/instance"
              xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
              xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-08-31/jppfs_cor">
            <xbrli:context id="ConsolidatedContext">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">EDI001</xbrli:identifier>
                    <xbrli:segment>
                        <xbrldi:explicitMember dimension="jppfs_cor:ConsolidatedOrNonConsolidatedAxis">
                            jppfs_cor:ConsolidatedMember
                        </xbrldi:explicitMember>
                    </xbrli:segment>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:instant>2025-03-31</xbrli:instant>
                </xbrli:period>
            </xbrli:context>
            <xbrli:context id="NonConsolidatedContext">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">EDI001</xbrli:identifier>
                    <xbrli:segment>
                        <xbrldi:explicitMember dimension="jppfs_cor:ConsolidatedOrNonConsolidatedAxis">
                            jppfs_cor:NonConsolidatedMember
                        </xbrldi:explicitMember>
                    </xbrli:segment>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:instant>2025-03-31</xbrli:instant>
                </xbrli:period>
            </xbrli:context>
        </xbrl>"""
        
        root = ET.fromstring(xbrl_mixed)
        # Should return True because ConsolidatedMember exists
        self.assertTrue(self.extractor._has_consolidated_data(root))
    
    def test_legacy_context_ref_pattern(self):
        """Test fallback pattern for contextRef containing Consolidated"""
        xbrl_legacy = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance">
            <NetSales contextRef="ConsolidatedCurrentYear">1000000</NetSales>
        </xbrl>"""
        
        root = ET.fromstring(xbrl_legacy)
        self.assertTrue(self.extractor._has_consolidated_data(root))
    
    def test_empty_xbrl_document(self):
        """Test with empty XBRL document"""
        xbrl_empty = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance">
        </xbrl>"""
        
        root = ET.fromstring(xbrl_empty)
        self.assertFalse(self.extractor._has_consolidated_data(root))


if __name__ == '__main__':
    unittest.main()