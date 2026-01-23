# 승강제 확산이 리그 관중 증대에 미치는 영향 분석
> ### K3리그 승강제 도입의 타당성 및 '흥미로운 경기' 지표 발굴을 중심으로

### Team
---
| **성명** | **김재빈** | **김대훈** |
| :---: | :---: | :---: |
| **프로필** | <a href="https://github.com/JaeBinary"><img src="https://github.com/JaeBinary.png" width="100"></a> | <a href="https://github.com/Virum123"><img src="https://github.com/Virum123.png" width="100"></a> |
| **소속** | AI SeSAC | AI SeSAC |
| **역할** | **Data Engineering**<br>(K/J-League ETL & H/W Metric) | **Data Analysis**<br>(EPL/EFL Insight & Visualization) |

### Background
---
**[AS-IS] : K리그의 구조적 한계와 정체**
- 현재 K리그는 1~2부 간의 제한적 승강제만 시행 중이며, 3부(K3) 이하로의 개방은 초기 논의 단계임.
- 구조적 폐쇄성으로 인해 한국 축구 관중 수는 인구 대비 약 **6%** 수준에서 장기간 정체 중.

**[TO-BE] : 벤치마킹 모델 (J-League)**
- 이웃 국가인 일본은 J3까지 승강제 시스템(Pyramid System)이 완전히 정착됨.
- 지역 밀착과 리그의 역동성을 바탕으로 총 관중 수가 인구 대비 10%에 육박함.

**[Problem Definition]**
> **"리그 구조의 확장이 필연적으로 관중 증대를 담보하는가?"**
1. 단순한 제도 도입을 넘어, '빈번한 리그 구성의 변화(League Churn)'가 팬덤에 미치는 심리적 영향을 규명해야 함.
2. 관중을 경기장으로 불러들이는 '흥미로운 경기'의 정의를 정성적 느낌이 아닌, 정량적 데이터(활동량, 스프린트 등)로 입증해야 함.

### Key Hypotheses
---
본 프로젝트는 "역동성이 흥행을 이끈다"는 대전제를 증명하기 위해 다음 3단계 가설을 검증한다.

#### 1. Main Hypothesis : 리그 유동성(Liquidity)과 관중의 상관관계
> **"리그 구성 팀의 빈번한 변화(High Churn Rate)는 리그 전체의 총 관중 수(Total Attendance)를 증가시킨다."**
- **논거:** 고정된 대진은 피로감을 유발하나, 승강제에 의한 새로운 팀의 유입은 '매치업의 희소성(Novelty)'과 '새로운 서사(Narrative)'를 부여하여 잠재 관중을 깨운다.

#### 2. Sub-Hypothesis A : '흥미'의 정량화 (Quality of Match)
> **"경기 내 물리적 활동량(Activity Level)이 높은 경기는 '재미있는 경기'로 인식되어 관중 재방문율을 높인다."**
- **지표 정의:** '재미'라는 추상적 개념을 **`Sprint Count(스프린트 횟수)`**와 **`Total Distance(총 이동 거리)`**로 치환하여 분석.
- **예상 결과:** 강등/승격권이 걸린 치열한 경기일수록 활동량이 높고, 이것이 직관 만족도와 양의 상관관계를 가질 것이다.

#### 3. Sub-Hypothesis B : 승격 팀의 '언더독 효과' (Promotion Bump)
> **"하부 리그에서 승격한 팀은 '기대 심리'와 '성취감'으로 인해 잔류 팀 대비 높은 관중 증가율(YoY)을 기록한다."**
- **비교군:** 잉글랜드(입스위치, 레스터 시티) 및 일본(J2→J1, J3→J2) 승격 팀의 관중 데이터 분석.

### Methodology & Data Strategy
---
#### 1. Analytical Scope (분석 범위)
| 구분 | 대상 (Target) | 분석 목적 |
| :--- | :--- | :--- |
| **Macro** | **J-League (J1~J3)** | 승강제 정착 모델의 구조적 특징 및 리그별 관중 격차 분석 |
| **Micro** | **EPL / EFL** | 드라마틱한 승격/강등 사례(Case Study)를 통한 '변화의 파급력' 측정 |
| **Metric** | **Tracking Data** | 선수 활동량(스프린트, 활동 거리) 데이터와 관중 수의 상관관계 도출 |

#### 2. Data Engineering (ERD 설계안)
데이터의 일관성과 분석 용이성을 위해 `Snowflake Schema` 형태로 데이터를 구축한다.

* **`League_Meta`**: 리그 기본 정보 (국가, 시즌, 티어, 승강제 여부)
* **`Team_Stats`**: 시즌별 팀 성적 (순위, 승점, 승격/강등 여부, 평균 관중)
* **`Match_Log`**: 경기별 상세 기록 (매치업, 경기장, 날씨, **총 관중 수**)
* **`Physical_Metrics`**: **[Core Data]** 경기별 활동량 데이터 (양 팀 총 이동 거리, 스프린트 횟수, 고강도 러닝 비율)

### R&R (Role & Responsibility)
---
#### 🧑🏻‍💻 **김재빈 (Data Engineer)**
* **J-League Data Pipeline 구축:** J1~J3 공식 기록 및 데이터 포털 크롤링 (Python, Selenium)
* **Physical Metric 확보:** 경기 활동량 지표(주행 거리, 스프린트 등) 수집 및 정제
* **Database Modeling:** 수집된 이기종 데이터(한/일/영)의 통합 DB 스키마 설계 및 적재

#### 🧑🏻‍💻 **김대훈 (Data Analyst)**
* **EPL/EFL Case Study:** 영국 리그 승격/강등 팀의 시계열 관중 추이 분석 (Time-series Analysis)
* **Visual Analysis:** '활동량'과 '관중 수'의 상관관계 시각화 (Scatter Plot, Regression Line)
* **Insight Derivation:** 데이터 기반의 K3 리그 활성화 전략 도출

### Expected Outcomes
---
1.  **정책적 제언:** 데이터에 근거한 'K3 승강제 도입의 기대 효과'를 수치(관중 증가 예상분)로 제시.
2.  **마케팅 인사이트:** "팬들은 많이 뛰는 팀을 보러 온다"는 가설 입증을 통해, 구단들에 '공격적/활동적 경기 운영'의 동기 부여 제공.
3.  **확장성:** 향후 K리그 공식 부가 데이터(Tracking Data) 도입 시 활용 가능한 분석 프레임워크 마련.

### References & Data Sources
---
#### 1. Target Domain Sources (Data Crawling)
* **K League Official Website:** `https://www.kleague.com/index.do`
    * *Purpose:* K리그 역대 관중 수 및 경기 일정 데이터 확보 (Control Group)
* **J League Official Website:** `https://www.jleague.jp`
    * *Purpose:* J1~J3 리그별 구조 파악 및 공식 경기 기록 수집 (Experimental Group)

#### 2. Tech Stack Documentation
* **Beautiful Soup 4:** `https://www.crummy.com/software/BeautifulSoup/bs4/doc`
    * *Usage:* 정적 웹 페이지(Static Page)의 HTML 파싱 및 데이터 추출
* **Selenium:** `https://www.selenium.dev/documentation`
    * *Usage:* 동적 웹 페이지(Dynamic Page) 제어 및 자바스크립트 렌더링 데이터 수집

#### 3. Internal Resources
* **Lecture Material:** Day7_0 - 정적 스크래이핑 (BeautifulSoup)
    * *Application:* 크롤러 설계 및 파싱 로직 구현 참조
