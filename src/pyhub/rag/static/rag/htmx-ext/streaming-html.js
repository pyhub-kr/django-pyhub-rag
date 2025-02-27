// MIT License
//
// Copyright (c) 2024. 파이썬사랑방

// 즉시 실행 함수를 정의합니다. 이는 전역 스코프를 오염시키지 않기 위함입니다.
(function () {
  // HTMX API 참조를 저장할 변수를 선언합니다.
  let api;

  // HTMX 확장을 정의합니다. 이름은 "streaming-html"입니다.
  htmx.defineExtension("streaming-html", {
    // 초기화 함수: HTMX API 참조를 저장합니다.
    init: function (apiRef) {
      api = apiRef;
    },
    // 이벤트 처리 함수: HTMX 이벤트를 처리합니다.
    onEvent: async function (eventName, event) {
      const currentElement = event.target || event.detail.elt;

      // 'htmx:beforeRequest' 이벤트를 처리합니다.
      if (currentElement.getAttribute("hx-ext") === "streaming-html") {
        if (eventName === "htmx:beforeRequest") {
          // 현재 이벤트 대상 요소를 가져옵니다.
          await this.processRequest(currentElement, event);
        }
      }
    },
    processRequest: async function (currentElement, event) {
      event.preventDefault();

      // hx-target 속성으로 지정된 대상 요소를 찾습니다.
      const targetElement = api.getTarget(currentElement);

      // 현재 요소가 'streaming-html' 확장을 사용하는지 확인합니다.
      if (currentElement.getAttribute("hx-ext") === "streaming-html") {
        // HTMX의 기본 요청을 방지합니다.
        event.preventDefault();

        // 기본 fetch 메서드와 URL을 설정합니다.
        let fetchMethod = "get";
        let fetchUrl = currentElement.action || "";
        let fetchBody = null;

        // HTTP 메서드와 URL을 결정합니다.
        for (const httpMethod of ["get", "post", "put", "delete", "patch"]) {
          const url = currentElement.getAttribute(`hx-${httpMethod}`);
          if (url) {
            fetchMethod = httpMethod;
            fetchUrl = url;
            break;
          }
        }

        if (currentElement instanceof HTMLFormElement) {
          const formData = new FormData(currentElement);
          const params = new URLSearchParams(formData);
          // GET 요청의 경우, 쿼리 문자열에 폼 데이터를 추가합니다.
          if (fetchMethod === "get") {
            fetchUrl +=
              (fetchUrl.includes("?") ? "&" : "?") + params.toString();
            fetchBody = undefined;
          } else {
            fetchBody = formData;
          }
        } else {
          fetchBody = undefined;
        }

        // fetch API를 사용하여 요청을 보냅니다.
        try {
          const response = await fetch(fetchUrl, {
            method: fetchMethod,
            body: fetchBody,
            headers: {
              "HX-Request": "true",
            },
          });

          // 응답 본문을 읽기 위한 reader를 생성합니다.
          const reader = response.body.getReader();
          // 텍스트 디코더를 생성합니다.
          const textDecoder = new TextDecoder();
          // 청크 카운터를 초기화합니다. chunk 이벤트 발생 횟수로서 사용됩니다.
          let chunkCount = 0;

          // 응답 스트림을 청크 단위로 처리합니다.
          while (true) {
            const { done, value } = await reader.read();
            if (!done) {
              // 청크를 디코드합니다.
              let responseHtml = textDecoder.decode(value);
              // 스왑 사양을 가져옵니다.
              const swapSpec = api.getSwapSpecification(currentElement);

              // 확장을 통해 응답을 변환합니다.
              api.withExtensions(targetElement, function (extension) {
                responseHtml = extension.transformResponse(
                  responseHtml,
                  null,
                  targetElement,
                );
              });

              // 대상 요소에 응답 HTML을 스왑합니다.
              api.swap(targetElement, responseHtml, swapSpec);

              // 청크 이벤트를 트리거합니다.
              htmx.trigger(currentElement, "chunk", {
                elt: currentElement,
                target: targetElement,
                requestConfig: {},
                count: chunkCount++,
              });
            } else {
              // 스트리밍이 완료되면 afterSettle 이벤트를 수동으로 트리거
              htmx.trigger(currentElement, "htmx:afterSettle", {
                elt: currentElement,
                target: targetElement,
                requestConfig: {},
              });

              // 스트림이 끝나면 루프를 종료합니다.
              break;
            }
          }
        } catch (error) {
          // 오류가 발생하면 콘솔에 로그를 출력합니다.
          console.error("Error:", error);
        }
      }
    },
  });
})();
