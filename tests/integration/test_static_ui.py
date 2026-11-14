"""Integration tests for the static web interface mounted at /ui."""


def test_ui_root_serves_html(client):
    response = client.get("/ui/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_ui_stylesheet_is_served(client):
    response = client.get("/ui/css/styles.css")
    assert response.status_code == 200


def test_api_root_route_unchanged(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Financial Analytics System API",
        "version": "1.0.0",
    }


def test_ui_javascript_modules_are_served(client):
    for path in ("/ui/js/api.js", "/ui/js/layout.js", "/ui/js/login.js"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_ui_application_pages_are_served(client):
    for path in ("/ui/workspace.html", "/ui/department.html"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html")


def test_ui_unknown_path_returns_404(client):
    response = client.get("/ui/does-not-exist.html")
    assert response.status_code == 404
