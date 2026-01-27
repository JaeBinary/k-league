# 트러블슈팅

스크래퍼 사용 중 발생할 수 있는 오류와 해결 방법을 정리한 문서입니다.

## J리그 스크래퍼 오류

### TimeoutException

#### 증상

```
selenium.common.exceptions.TimeoutException: Message: timeout 10 sec
```

페이지 로딩이 지정된 시간 내에 완료되지 않아 발생합니다.

#### 원인

- 네트워크 연결이 불안정함
- J리그 서버 응답이 느림
- 트래킹 데이터 탭이 없는 경기

#### 해결 방법

**방법 1: 순차 처리로 전환**

병렬 처리 시 네트워크 부하가 증가하여 타임아웃이 발생할 수 있습니다.

```python
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=False  # 순차 처리
)
```

**방법 2: 워커 수 감소**

병렬 워커 수를 줄여 서버 부하를 낮춥니다.

```python
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=2  # 기본값 4에서 감소
)
```

**방법 3: 재실행**

일시적인 네트워크 문제인 경우 재실행하면 해결됩니다.

---

### SessionNotCreatedException

#### 증상

```
selenium.common.exceptions.SessionNotCreatedException: Message: session not created
```

ChromeDriver 세션 생성에 실패했습니다.

#### 원인

- Chrome 브라우저와 ChromeDriver 버전 불일치
- ChromeDriver가 설치되지 않음
- 시스템 리소스 부족

#### 해결 방법

**방법 1: ChromeDriver 버전 확인**

Chrome 버전과 ChromeDriver 버전이 일치하는지 확인합니다.

```bash
# Chrome 버전 확인 (Windows)
"C:\Program Files\Google\Chrome\Application\chrome.exe" --version

# ChromeDriver 버전 확인
chromedriver --version
```

**방법 2: ChromeDriver 업데이트**

```bash
# macOS
brew upgrade chromedriver

# Windows (Chocolatey)
choco upgrade chromedriver
```

**방법 3: 워커 수 감소**

메모리 부족으로 인한 세션 생성 실패 시 워커 수를 줄입니다.

```python
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    max_workers=2
)
```

---

### NoSuchElementException

#### 증상

```
selenium.common.exceptions.NoSuchElementException: Message: no such element
```

페이지에서 필요한 HTML 요소를 찾을 수 없습니다.

#### 원인

- 웹사이트 구조 변경
- 경기 데이터가 아직 등록되지 않음
- 페이지 로딩 불완전

#### 해결 방법

**방법 1: 데이터 존재 여부 확인**

경기가 아직 진행되지 않은 경우 데이터가 없을 수 있습니다. 시즌이 완료된 후 수집하세요.

**방법 2: 웹사이트 확인**

브라우저에서 해당 경기 페이지를 직접 확인하여 구조 변경 여부를 확인합니다.

---

### 트래킹 데이터가 None

#### 증상

`HomeDistance`, `AwayDistance`, `HomeSprint`, `AwaySprint` 필드가 모두 `None`입니다.

#### 원인

- 트래킹 데이터는 2019년 이후 경기부터 제공
- 일부 경기장에서 트래킹 장비 미설치
- 경기 취소 또는 몰수

#### 해결 방법

이는 정상적인 동작입니다. 데이터 분석 시 결측치를 처리하세요.

```python
import pandas as pd

df = pd.DataFrame(data)

# 트래킹 데이터가 있는 경기만 필터링
df_with_tracking = df.dropna(subset=['HomeDistance'])

# 또는 결측치를 0으로 대체
df['HomeDistance'] = df['HomeDistance'].fillna(0)
```

---

## K리그 스크래퍼 오류

### 지원하지 않는 리그 오류

#### 증상

```
⛔ 지원하지 않는 리그: K리그3
   지원 리그: ['K리그1', 'K리그2', '승강PO', '슈퍼컵']
```

#### 원인

잘못된 리그명을 입력했습니다.

#### 해결 방법

지원되는 리그명을 정확히 입력합니다.

```python
# 올바른 리그명
data, filename = collect_kleague_match_data(
    year=2025,
    league="K리그1"  # K리그1, K리그2, 승강PO, 슈퍼컵
)
```

---

### 데이터 누락

#### 증상

일부 경기 데이터가 수집되지 않습니다.

#### 원인

- 경기가 아직 진행되지 않음
- 경기 취소 또는 연기
- 웹사이트 데이터 미등록

#### 해결 방법

**방법 1: 시즌 완료 후 수집**

시즌이 완료된 후 전체 데이터를 수집하면 누락이 최소화됩니다.

**방법 2: 수집 결과 확인**

```python
import pandas as pd

df = pd.DataFrame(data)
print(f"수집된 경기 수: {len(df)}")
print(f"연도별 분포:\n{df.groupby('Meet_Year').size()}")
```

---

### 파싱 오류

#### 증상

특정 필드 값이 예상과 다르거나 `None`입니다.

```
❌ 리그명 정보를 찾을 수 없습니다.
❌ 팀 정보를 찾을 수 없습니다.
```

#### 원인

- 웹사이트 HTML 구조 변경
- 비정상적인 데이터 형식

#### 해결 방법

브라우저 개발자 도구로 웹사이트 구조를 확인하고, 필요시 CSS 선택자를 업데이트합니다.

---

## 공통 오류

### 메모리 부족

#### 증상

```
MemoryError: Unable to allocate...
```

또는 시스템이 느려지고 응답이 없음.

#### 원인

대량의 데이터 수집 시 메모리 사용량 증가.

#### 해결 방법

**방법 1: 분할 수집**

연도를 나누어 수집합니다.

```python
import pandas as pd

for year in [2020, 2021, 2022, 2023, 2024, 2025]:
    data, filename = collect_kleague_match_data(year=year, league="K리그1")
    pd.DataFrame(data).to_csv(f"data/{filename}.csv", index=False)
    del data  # 메모리 해제
```

**방법 2: 워커 수 감소 (J리그)**

```python
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    max_workers=2  # 메모리 사용량 감소
)
```

---

### 네트워크 연결 오류

#### 증상

```
requests.exceptions.ConnectionError: HTTPSConnectionPool...
urllib3.exceptions.MaxRetryError: Max retries exceeded
```

#### 원인

- 인터넷 연결 불안정
- 방화벽 또는 프록시 차단
- 대상 서버 다운

#### 해결 방법

**방법 1: 네트워크 확인**

인터넷 연결 상태를 확인합니다.

```bash
ping www.kleague.com
ping www.jleague.jp
```

**방법 2: VPN 사용**

특정 지역에서 접근이 제한된 경우 VPN을 사용합니다.

**방법 3: 재시도**

일시적인 네트워크 문제인 경우 잠시 후 재시도합니다.

---

## 도움 요청

위 해결 방법으로 문제가 해결되지 않으면 다음 정보와 함께 이슈를 제출해 주세요.

- 사용한 코드
- 전체 오류 메시지
- Python 버전 (`python --version`)
- 운영체제 정보
- (J리그) Chrome 및 ChromeDriver 버전
