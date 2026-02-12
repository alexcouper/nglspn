from django.http import HttpRequest, HttpResponse


def health(request: HttpRequest) -> HttpResponse:
    return HttpResponse("OK")


def home(request: HttpRequest) -> HttpResponse:
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>naglasúpan</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fafafa;
        }
        img {
            max-width: 200px;
            height: auto;
        }
    </style>
</head>
<body>
    <img src="/static/naglasupan.svg" alt="Naglasúpan">
</body>
</html>"""
    return HttpResponse(html)
