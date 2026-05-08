from quickdb.scripts.stub_generator import _to_pascal_case, _class_to_filename


def test_to_pascal_case_single_word():
    assert _to_pascal_case('cases') == 'Cases'


def test_to_pascal_case_snake_case():
    assert _to_pascal_case('case_updates') == 'CaseUpdates'


def test_to_pascal_case_single_segment():
    assert _to_pascal_case('suitecrm') == 'Suitecrm'


def test_to_pascal_case_multi_segment():
    assert _to_pascal_case('my_warehouse') == 'MyWarehouse'


def test_class_to_filename_sqlserver():
    assert _class_to_filename('SQLServer') == 'sql_server.pyi'


def test_class_to_filename_suitecrm():
    assert _class_to_filename('SuiteCRMServer') == 'suite_crm_server.pyi'


def test_class_to_filename_mariadb():
    assert _class_to_filename('MariaDBServer') == 'maria_db_server.pyi'


def test_class_to_filename_simple():
    assert _class_to_filename('MyServer') == 'my_server.pyi'
