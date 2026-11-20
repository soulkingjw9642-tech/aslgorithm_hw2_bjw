# 명세 초안: URL 단축기

이 문서는 구현 전에 검토할 URL 단축기 명세 초안이다. 구현은 Python 표준
라이브러리만 사용한다. 저장소의 `src/`에서는 `dict`, `set`, 내장 `hash()`를
사용하지 않으며, 키-값 저장은 직접 구현한 해시 테이블로 처리한다.

## 1. 무엇을 만드는가

사용자는 HTTP 또는 HTTPS URL을 단축해 짧은 코드를 받고, 그 코드로 원래
URL을 찾는다. 데이터는 프로세스 메모리에 저장하며 서버를 재시작하면 초기화된다.

## 2. base62 인코딩

`src.base62`는 `encode(n)`과 `decode(s)`를 제공한다. 알파벳 순서는
`0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`다.

- `encode(n)`은 음이 아닌 정수를 인코딩한다. `0`은 `"0"`이다.
- 음수는 `ValueError`, 정수가 아닌 입력(불리언 포함)은 `TypeError`다.
- `decode(s)`는 비어 있지 않은 문자열만 받으며, 알파벳 밖의 문자는 `ValueError`다.
- 디코딩 결과는 음이 아닌 정수다. 대소문자는 서로 다른 숫자를 나타낸다.

## 3. 해시 테이블

`HashTable(capacity=...)`는 개별 체이닝(separate chaining)을,
`LinearProbingHashTable(capacity=...)`는 선형 탐지를 사용한다. 두 테이블은 같은
저장·조회 인터페이스를 제공하고 용량은 양의 정수로 고정한다. 자동 크기 변경은
하지 않는다.

- 키와 값은 문자열이다. `put(key, value)`는 새 키를 저장하고 기존 키의 값은
  갱신한다. `get(key)`는 값 또는 키가 없을 때 `None`을 돌려준다.
- `size`는 고유 키 수다. `items()`는 저장된 키-값 쌍을 순회한다.
- 해시 함수는 키의 문자를 왼쪽부터 Horner 방식으로 누적한다. 각 문자에 대해
  `h = (h * 31 + ord(character)) % capacity`를 계산한다. 빈 문자열의 버킷은 0이다.
- `bucket_index(key)`는 버킷 인덱스를 반환한다. `hash_trace(key)`는 문자마다
  `(문자, Unicode 코드 포인트, 누적 나머지)`를 순서대로 제공한다.
- `find_with_probes(key)`는 `(value, probes)`를 반환한다. `probes`는 체이닝에서
  비교한 노드 수, 선형 탐지에서 확인한 칸 수다. 키가 없으면 값은 `None`이다.
- `probe_trace(key)`는 탐색 중 확인한 칸의 인덱스를 순서대로 반환한다.
- 선형 탐지는 Horner 해시로 구한 시작 칸부터 `(home + step) % capacity` 순서로
  조사한다. 가득 찬 테이블에 새 키를 넣으면 `OverflowError`가 발생한다.
- `URLShortener`는 테이블 구현을 주입받을 수 있어 두 충돌 처리 방식을 바꿔
  사용할 수 있다.
- 키나 값이 문자열이 아니면 `TypeError`다. 용량이 양의 정수가 아니면
  `ValueError`다.

## 4. 단축기

`URLShortener`는 `shorten(url)`과 `expand(code)`를 제공한다.

- 입력은 앞뒤 공백이 없는 절대 URL이어야 하며 `http` 또는 `https` 스킴과
  호스트명을 가져야 한다. 잘못된 URL은 `ValueError`, 문자열이 아닌 입력은
  `TypeError`다.
- 같은 URL 문자열을 다시 단축하면 기존 코드를 반환한다.
- 새 코드는 0부터 증가하는 정수 ID를 base62로 인코딩해 만든다. 생성된 코드는
  해시 테이블에 URL과 함께 저장한다. 해시값 자체를 단축 코드로 사용하지 않는다.
- `expand(code)`는 저장된 URL 또는 코드가 없을 때 `None`을 돌려준다.
- 비어 있거나 base62 알파벳에 없는 코드는 `ValueError`, 문자열이 아닌 코드는
  `TypeError`다.

## 5. 웹 서버

`make serve`는 기본 포트 8000에서 로컬 HTTP 서버를 실행한다. 루트 경로(`/`)는
URL 입력 폼을 보여주고 `POST /shorten`은 폼의 `url` 필드를 단축해 결과를
보여준다. `GET /<code>`는 코드가 있으면 원래 URL로 리다이렉트하고, 없으면
404를 반환한다. 기본 충돌 처리는 개별 체이닝이며, `make serve TABLE_TYPE=linear`로
선형 탐지 방식을 선택할 수 있다. `GET /table`은 선택된 방식의 칸, 탐색 경로와
Horner·선형 탐지 계산 근거를 보여준다.

단축 데이터는 프로세스 메모리에만 저장한다. 서버를 재시작하면 데이터는
초기화된다.

## 6. 경계 사례

- base62: 0, 1, 알파벳 경계(61/62), 큰 정수 왕복, 음수·잘못된 타입,
  빈 문자열·잘못된 문자
- 체이닝 및 선형 탐지: 빈 테이블 탐색, 충돌 키 저장, 중복 키 갱신, 없는 키,
  여러 용량, 잘못된 용량·키·값
- 선형 탐지: 마지막 칸에서 0번 칸으로 순환, 가득 찬 테이블 탐색과 삽입 거부
- 단축기: 정상 HTTP/HTTPS URL, 반복 입력의 동일 코드, 왕복 확장, 없는 코드,
  앞뒤 공백, 잘못된 스킴·호스트·포트·코드
- 웹: 루트 입력 화면, 정상 단축 요청, 잘못된 URL, 기존 코드 리다이렉트,
  없는 코드의 404, `/table`의 버킷과 계산 근거
