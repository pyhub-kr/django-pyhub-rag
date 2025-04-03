/* https://htmx.org/extensions/ws/ */

/* https://htmx.org/events/ */

function registerHtmxWsEventHandlers(el, eventHandlers) {
  const wsEventNames = [
    "htmx:wsConnecting",
    "htmx:wsOpen",
    "htmx:wsClose",
    "htmx:wsError",
    "htmx:wsBeforeMessage",
    "htmx:wsAfterMessage",
    "htmx:wsConfigSend",
    "htmx:wsBeforeSend",
    "htmx:wsAfterSend",
  ];
  wsEventNames.forEach((eventName) => {
    el.addEventListener(eventName, (event) => {
      const funcName = eventName.replace("htmx:", "");
      // camelCase를 kebab-case로 변환
      const triggerEventName = funcName.replace(
        /[A-Z]/g,
        (m) => `-${m.toLowerCase()}`,
      );

      // CustomEvent 생성 및 dispatch
      el.dispatchEvent(
        new CustomEvent(triggerEventName, {
          detail: event.detail,
          bubbles: true, // 이벤트 버블링 활성화
          cancelable: true, // 이벤트 취소 가능하도록 설정
        }),
      );

      if (eventHandlers) {
        const handler = eventHandlers[funcName];
        if (handler) {
          handler.call(eventHandlers, event);
        }
      }
    });
  });
}
