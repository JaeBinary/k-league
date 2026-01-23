<table width="100%" style="border-collapse: collapse; border: none;">
  <tr style="border: none;">
    <td align="center" bgcolor="#E3F2FD" style="padding: 20px; border: none;">
      <h1 style="margin: 0; color: #0D47A1;">⚽ 승강제 확산이 리그 관중 증대에 미치는 영향 분석</h1>
      <p style="margin: 10px 0 0 0; color: #546E7A;"><b>K3리그 승강제 도입의 타당성 및 '흥미로운 경기' 지표 발굴을 중심으로</b></p>
    </td>
  </tr>
</table>

<br>

### Team
---
| **성명** | **김재빈** | **김대훈** |
| :---: | :---: | :---: |
| **프로필** | <a href="https://github.com/JaeBinary"><img src="https://github.com/JaeBinary.png" width="100"></a> | <a href="https://github.com/Virum123"><img src="https://github.com/Virum123.png" width="100"></a> |
| **소속** | AI SeSAC | AI SeSAC |
| **역할** | **Data Engineering**<br>(J-League ETL & H/W Metric) | **Data Analysis**<br>(EPL/EFL Insight & Visualization) |

<br>

<table width="100%" style="border-collapse: collapse; border: none;">
  <tr style="border: none;">
    <td bgcolor="#F5F5F5" style="padding: 10px; border-left: 5px solid #0D47A1;">
      <h2 style="margin: 0;">1. Background</h2>
    </td>
  </tr>
</table>

**[AS-IS] : K리그의 구조적 한계와 정체**
- 현재 K리그는 1~2부 간의 제한적 승강제만 시행 중이며, 3부(K3) 이하로의 개방은 초기 논의 단계임.
- 구조적 폐쇄성으로 인해 한국 축구 관중 수는 인구 대비 약 **6%** 수준에서 장기간 정체 중.

**[TO-BE] : 벤치마킹 모델 (J-League)**
- 이웃 국가인 일본은 J3까지 승강제 시스템(Pyramid System)이 완전히 정착됨.
- 지역 밀착과 리그의 역동성을 바탕으로 총 관중 수가 인구 대비 **10%**에 육박함.

**[Problem Definition]**
> **"리그 구조의 확장이 필연적으로 관중 증대를 담보하는가?"**
> 1. 단순한 제도 도입을 넘어, **'빈번한 리그 구성의 변화(League Churn)'**가 팬덤에 미치는 심리적 영향을 규명해야 함.
> 2. 관중을 경기장으로 불러들이는 **'흥미로운 경기'**의 정의를 정성적 느낌이 아닌, **정량적 데이터(활동량, 스프린트 등)**로 입증해야 함.

<br>

<table width="100%" style="border-collapse: collapse; border: none;">
  <tr style="border: none;">
    <td bgcolor="#F5F5F5" style="padding: 10px; border-left: 5px solid #0D47A1;">
      <h2 style="margin: 0;">2. Key Hypotheses</h2>
    </td>
  </tr>
</table>

본 프로젝트는 **"역동성이 흥행을 이끈다"**는 대전제를 증명하기 위해 다음 3단계 가설을 검증한다.

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

<br>

<table width="100%" style="border-collapse: collapse; border: none;">
  <tr style="border: none;">
    <td bgcolor="#F5F5F5