#!/usr/bin/env python3
"""Замер скорости скачивания: 10 последовательных запросов к одному адресу."""

import argparse
import http.client
import ssl
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

REQUESTS = 10
CHUNK_SIZE = 64 * 1024
TIMEOUT_SECONDS = 30
USER_AGENT = "speedtest-script/1.0"


def make_ssl_context():
    """Обычная проверка сертификатов.

    У Python с python.org на macOS системного набора корневых сертификатов
    может не быть, пока не запущен "Install Certificates.command". В этом
    случае берём набор из certifi, если он установлен.
    """
    context = ssl.create_default_context()
    paths = ssl.get_default_verify_paths()
    if paths.cafile is None and paths.capath is None:
        try:
            import certifi
        except ImportError:
            pass
        else:
            context.load_verify_locations(certifi.where())
    return context


SSL_CONTEXT = make_ssl_context()


def download(url):
    """Скачивает ответ целиком и возвращает (секунды, байты)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    size = 0
    start = time.perf_counter()
    with urllib.request.urlopen(
        request, timeout=TIMEOUT_SECONDS, context=SSL_CONTEXT
    ) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
    return time.perf_counter() - start, size


def describe_error(error):
    if isinstance(error, urllib.error.HTTPError):
        return f"сервер ответил {error.code} {error.reason}"
    if isinstance(error, urllib.error.URLError):
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            return (
                f"не удалось проверить сертификат сервера ({error.reason.verify_message}). "
                "Если это Python с python.org на macOS, запустите "
                '"Install Certificates.command" из папки Python в Applications '
                "или выполните pip install certifi."
            )
        return str(error.reason)
    if isinstance(error, http.client.IncompleteRead):
        return "соединение оборвалось до конца ответа"
    return str(error) or type(error).__name__


def main():
    parser = argparse.ArgumentParser(
        description=f"Делает {REQUESTS} последовательных запросов к адресу "
        "и считает скорость скачивания."
    )
    parser.add_argument("url", help="адрес, например ссылка на тяжёлую картинку")
    args = parser.parse_args()

    parsed = urlparse(args.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        parser.error("нужен адрес вида http://... или https://...")

    total_seconds = 0.0
    total_bytes = 0
    for number in range(1, REQUESTS + 1):
        try:
            seconds, size = download(args.url)
        except (OSError, http.client.HTTPException) as error:
            print(
                f"Запрос {number}/{REQUESTS} не удался: {describe_error(error)}",
                file=sys.stderr,
            )
            return 1
        total_seconds += seconds
        total_bytes += size
        print(f"{number:>2}/{REQUESTS}  {seconds * 1000:>8.0f} мс  {size / 1e6:>8.2f} МБ")

    megabytes = total_bytes / 1e6
    megabytes_per_second = megabytes / total_seconds
    print()
    print(f"Среднее время запроса: {total_seconds / REQUESTS:.3f} с")
    print(f"Всего скачано:         {megabytes:.2f} МБ")
    print(
        f"Скорость скачивания:   {megabytes_per_second * 8:.2f} Мбит/с "
        f"({megabytes_per_second:.2f} МБ/с)"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПрервано.", file=sys.stderr)
        sys.exit(130)
