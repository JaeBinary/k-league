# 축구 리그 데이터 스크래퍼 시작하기

이 문서는 K리그와 J리그 경기 데이터를 자동으로 수집하는 스크래퍼 사용법을 안내합니다.

## 개요

축구 리그 스크래퍼는 공식 웹사이트에서 경기 정보를 자동으로 수집하는 도구입니다.

| 스크래퍼 | 데이터 소스 | 수집 데이터 |
|---------|------------|------------|
| K리그 스크래퍼 | [www.kleague.com](https://www.kleague.com) | 경기 메타데이터, 팀 정보, 경기장 환경 |
| J리그 스크래퍼 | [www.jleague.jp](https://www.jleague.jp) | 경기 메타데이터, 팀 정보, 트래킹 데이터 |

## 사전 요구사항

스크래퍼를 사용하기 전에 다음 환경이 필요합니다.

- Python 3.8 이상
- Chrome 브라우저 (J리그 스크래퍼용)
- ChromeDriver (J리그 스크래퍼용)

### 패키지 설치

```bash
pip install selenium beautifulsoup4 rich requests
```

### ChromeDriver 설치 (J리그용)

J리그 스크래퍼는 Selenium을 사용하므로 ChromeDriver가 필요합니다. Chrome 버전에 맞는 ChromeDriver를 설치하세요.

```bash
# macOS (Homebrew)
brew install chromedriver

# Windows (Chocolatey)
choco install chromedriver

# 또는 직접 다운로드
# https://chromedriver.chromium.org/downloads
```

## 빠른 시작

### K리그 데이터 수집

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data

# 2025년 K리그1 전체 시즌 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")
print(f"수집 완료: {len(data)}경기")
```

### J리그 데이터 수집

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data

# 2025년 J리그1 전체 시즌 수집
data, filename = collect_jleague_match_data(year=2025, league="J리그1")
print(f"수집 완료: {len(data)}경기")
```

## 다음 단계

- [K리그 스크래퍼 튜토리얼](./tutorials/kleague-tutorial.md): 단계별로 K리그 데이터 수집 방법을 배웁니다.
- [J리그 스크래퍼 튜토리얼](./tutorials/jleague-tutorial.md): J리그 트래킹 데이터까지 수집하는 방법을 배웁니다.
- [아키텍처 이해하기](./explanations/architecture.md): 스크래퍼의 내부 동작 원리를 이해합니다.
- [API 레퍼런스](./reference/kleague-api.md): 상세한 함수 사용법을 확인합니다.
