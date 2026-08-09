"""Phục vụ file media có hỗ trợ HTTP Range (cần để tua audio/video)."""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import http_date
from django.views.static import was_modified_since
from django.utils._os import safe_join

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def _iter_file(file_obj, length: int, chunk_size: int = 64 * 1024):
    remaining = length
    try:
        while remaining > 0:
            chunk = file_obj.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        file_obj.close()


def serve_media_with_range(request, path: str):
    """
    Serve MEDIA_ROOT/<path> với Accept-Ranges / 206 Partial Content.
    Django static.serve + Daphne không xử lý Range → không tua được file lớn.
    """
    document_root = Path(settings.MEDIA_ROOT)
    try:
        fullpath = Path(safe_join(str(document_root), path))
    except ValueError as exc:
        raise Http404("Invalid path") from exc

    if not fullpath.is_file():
        raise Http404(f"{path} does not exist")

    statobj = fullpath.stat()
    if not was_modified_since(
        request.META.get("HTTP_IF_MODIFIED_SINCE"),
        statobj.st_mtime,
    ):
        return HttpResponse(status=304)

    content_type, encoding = mimetypes.guess_type(str(fullpath))
    content_type = content_type or "application/octet-stream"
    file_size = statobj.st_size
    range_header = (request.META.get("HTTP_RANGE") or "").strip()

    if range_header:
        match = _RANGE_RE.fullmatch(range_header)
        if not match:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            return response

        start_s, end_s = match.groups()
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
        if end >= file_size:
            end = file_size - 1

        if start >= file_size or start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            return response

        length = end - start + 1
        file_obj = fullpath.open("rb")
        file_obj.seek(start)
        response = StreamingHttpResponse(
            _iter_file(file_obj, length),
            status=206,
            content_type=content_type,
        )
        response["Content-Length"] = str(length)
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Accept-Ranges"] = "bytes"
        response["Last-Modified"] = http_date(statobj.st_mtime)
        if encoding:
            response["Content-Encoding"] = encoding
        return response

    response = FileResponse(fullpath.open("rb"), content_type=content_type)
    response["Content-Length"] = str(file_size)
    response["Accept-Ranges"] = "bytes"
    response["Last-Modified"] = http_date(statobj.st_mtime)
    if encoding:
        response["Content-Encoding"] = encoding
    return response
