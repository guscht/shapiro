from fastapi.testclient import TestClient
from shapiro import shapiro_server
import os
import json

shapiro_server.CONTENT_DIR = './test/ontologies'

shapiro_server.init()

client = TestClient(shapiro_server.app)

def test_get_server():
    server = shapiro_server.get_server('127.0.0.1', 8000, shapiro_server.CONTENT_DIR, 'info', 'text/turtle')
    assert server is not None

def test_bad_schema_checking_with_bad_schemas():
    result = shapiro_server.check_schemas(shapiro_server.CONTENT_DIR)
    assert len(result) == 4
    assert './test/ontologies/bad/person1_without_origin_on_this_server.jsonld' in shapiro_server.BAD_SCHEMAS
    assert './test/ontologies/bad/person2_without_origin_on_this_server.ttl' in shapiro_server.BAD_SCHEMAS

def test_bad_schema_checking_without_bad_schemas():
    result = shapiro_server.check_schemas('./test/ontologies/com')
    assert len(result) == 0

def test_get_existing_bad_schemas():
    result = shapiro_server.check_schemas(shapiro_server.CONTENT_DIR)
    assert len(result) == 4
    response = client.get("/bad/person1_with_syntax_error")
    assert response.status_code == 406
    mime = 'application/ld+json'
    response = client.get("/bad/person2_with_syntax_error", headers={"accept-header": mime})
    assert response.status_code == 406

def test_commandline_parse_to_default():
    args = shapiro_server.get_args([])
    assert args.host == '127.0.0.1'
    assert args.port == 8000
    assert args.content_dir == './'
    assert args.log_level == 'info'
    assert args.default_mime == 'text/turtle'
    assert args.features == 'all'

def test_commandline_parse_to_specified_values():
    args = shapiro_server.get_args(['--host', '0.0.0.0', '--port', '1234', '--content_dir', './foo', '--log_level', 'bar', '--default_mime', 'foobar', '--features', 'validate'])
    assert args.host == '0.0.0.0'
    assert args.port == 1234
    assert args.content_dir == './foo'
    assert args.log_level == 'bar'
    assert args.default_mime == 'foobar'
    assert args.features == 'validate'

def test_get_non_existing_schema():
    response = client.get("/this_is_a_non_existing_ontology")
    assert response.status_code == 404

def test_get_existing_jsonld_schema_as_jsonld():
    mime = 'application/ld+json'
    response = client.get("/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(mime)
    assert response.status_code == 200

def test_get_existing_jsonld_schema_as_jsonld_with_multiple_weighted_accept_headers():
    mime_in = 'application/ld+json;q=0.9,text/turtle;q=0.8'
    mime_out = 'application/ld+json'
    response = client.get("/person", headers={"accept-header": mime_in})
    assert response.headers['content-type'].startswith(mime_out)
    assert response.status_code == 200

def test_get_existing_jsonld_schema_as_ttl():
    mime = 'text/turtle'
    response = client.get("/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(mime)
    assert response.status_code == 200

def test_get_existing_ttl_schema_deep_down_in_the_hierarchy_as_jsonld():
    mime = 'application/ld+json'
    response = client.get("/com/example/org/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(mime)
    assert response.status_code == 200

def test_get_existing_ttl_schema_deep_down_in_the_hierarchy_as_jsonld_ignoring_element_reference_with_os_path_sep():
    mime = 'application/ld+json'
    response = client.get("/com/example/org/person/firstname", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(mime)
    assert response.status_code == 200

def test_get_existing_ttl_schema_deep_down_in_the_hierarchy_as_jsonld_ignoring_element_reference_with_anchor():
    mime = 'application/ld+json'
    response = client.get("/com/example/org/person#firstname", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(mime)
    assert response.status_code == 200

def test_get_existing_ttl_schema_deep_down_in_the_hierarchy_as_ttl():
    mime = 'text/turtle'
    response = client.get("/com/example/org/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(mime)
    assert response.status_code == 200

def test_get_existing_jsonld_schema_as_default_without_accept_header():
    mime = ''
    response = client.get("/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(shapiro_server.MIME_DEFAULT)
    assert response.status_code == 200

def test_get_existing_ttl_schema_as_default_without_accept_header():
    mime = ''
    response = client.get("/com/example/org/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(shapiro_server.MIME_DEFAULT)
    assert response.status_code == 200

def test_get_existing_schema_with_duplicates():
    response = client.get("/dupes/person")
    assert response.status_code == 404

def test_get_existing_schema_with_uncovered_mime_type():
    mime = 'text/text'
    response = client.get("/com/example/org/person", headers={"accept-header": mime})
    assert response.headers['content-type'].startswith(shapiro_server.MIME_DEFAULT)
    assert response.status_code == 200

def test_convert_with_unkown_mime_yields_none():
    result = shapiro_server.convert('irrelevantPath', 'irrelevantContent', 'fantasymimetype')
    assert result is None

def test_validate_with_compliant_jsonld_data():
    with open('./test/data/person2_data_valid.jsonld') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == True

def test_validate_with_uncompliant_jsonld_data():
    with open('./test/data/person2_data_invalid.jsonld') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == False

def test_validate_with_compliant_jsonld_list_data():
    with open('./test/data/person_list1_data_valid.jsonld') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == True

def test_validate_with_uncompliant_jsonld_list_data():
    with open('./test/data/person_list1_data_invalid.jsonld') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == False

def test_validate_with_compliant_ttl_data():
    with open('./test/data/person1_data_valid.ttl') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_TTL})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == True

def test_validate_with_uncompliant_ttl_data():
    with open('./test/data/person1_data_invalid.ttl') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_TTL})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == False

def test_validate_with_compliant_ttl_list_data():
    with open('./test/data/person_list2_data_valid.ttl') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_TTL})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == True

def test_validate_with_uncompliant_ttl_list_data():
    with open('./test/data/person_list2_data_invalid.ttl') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_TTL})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == False

def test_validate_with_syntax_error_ttl_data():
    with open('./test/data/person1_data_syntax_error.ttl') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_TTL})
        assert response.status_code == 422

def test_validate_with_syntax_error_jsonld_data():
    with open('./test/data/person2_data_syntax_error.jsonld') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.status_code == 422

def test_validate_with_unsupported_data_content_type():
        response = client.post("/validate/com/example/org/person", "irrelevant", headers={"content-type": 'text/text'})
        assert response.status_code == 415

def test_validate_with_remote_schema_that_cannot_be_found():
    with open('./test/data/person2_data_valid.jsonld') as data_file:
        response = client.post("/validate/schema.org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.status_code == 422

def test_validate_with_local_schema_that_cannot_be_found():
    with open('./test/data/person2_data_valid.jsonld') as data_file:
        response = client.post("/validate/foo", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.status_code == 422

def test_validate_with_remote_schema():
    with open('./test/data/person2_data_valid.jsonld') as data_file:
        response = client.post("/validate/www.w3.org/2000/01/rdf-schema", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        assert response.status_code == 200
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == True

def test_features_switching_only_serve():
    shapiro_server.activate_routes('serve')
    response = client.get("/person")
    assert response.status_code == 200
    response = client.post("/validate/com/example/org/person", "irrelevant content", headers={"content-type": shapiro_server.MIME_TTL})
    # with the validate route disabled, the request will land with the get_schema route and therefore return a 405 (and not a 404)
    assert response.status_code == 405

def test_features_switching_only_validate():
    shapiro_server.activate_routes('validate')
    response = client.get("/person")
    assert response.status_code == 404
    with open('./test/data/person2_data_invalid.jsonld') as data_file:
        response = client.post("/validate/com/example/org/person", data_file.read(), headers={"content-type": shapiro_server.MIME_JSONLD})
        assert response.status_code == 200
        assert response.headers['content-type'].startswith(shapiro_server.MIME_JSONLD)
        report = response.json()
        assert report[0]['http://www.w3.org/ns/shacl#conforms'][0]['@value'] == False
