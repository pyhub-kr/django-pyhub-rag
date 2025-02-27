/* static/cotton/widgets/image_preview_file.js */

function initImagePreviewFile(componentEl, previewDisplayEl, withBase64Field) {
  const inputEl = componentEl.querySelector("input[type=file]");
  const formEl = inputEl.closest("form");
  let base64Field;

  if (withBase64Field) {
    base64Field = document.createElement("input");
    // 서버 Consumer에서도 필드명이 __base64로 끝나면 base64 데이터로서 파싱토록 구현되어있습니다.
    base64Field.name = `${inputEl.name}__base64`;
    base64Field.type = "hidden";
    formEl.append(base64Field);
  }

  inputEl.addEventListener("change", async function () {
    // 비동기 함수로 변경하여, base64 인코딩 요소를 준비하는 동안 대기하기
    await previewImages();
    // previewDisplayEl 내의 img 태그를 모두 가져와서, base64Field 값으로서 base64 이미지를 배열로서 모두 저장
    if (withBase64Field) {
      const images = previewDisplayEl.querySelectorAll("img");
      const base64Images = Array.from(images).map((img) => img.src);
      // 각 이미지에 대한 base64 문자열을 구분자(||)로 이어 붙이기
      // 서버 Consumer에서도 ||를 통해 base64 문자열을 분리토록 구현되어있습니다.
      base64Field.value = base64Images.join("||");
    }
  });

  formEl?.addEventListener("reset", function () {
    if (previewDisplayEl) previewDisplayEl.innerHTML = "";
  });

  async function previewImages() {
    if (!previewDisplayEl) {
      console.warn("previewDisplayEl is not defined");
      return;
    }

    previewDisplayEl.innerHTML = "";
    if (!inputEl.files) {
      console.warn("[previewImages] input is", inputEl);
    } else {
      const filesArray = Array.from(inputEl.files);

      const promises = filesArray.map((currentFile) => {
        return new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = function (e) {
            const imageDataUrl = e.target.result;
            const container = document.createElement("div");
            container.className = "relative";

            const img = document.createElement("img");
            img.src = imageDataUrl;
            img.className = "w-[75px] h-[75px] object-cover rounded-lg";
            container.appendChild(img);

            /*
            removeButton.type = "button"을 명시하지 않으면, text enter 입력 시에 removeButton이 클릭되는 현상.

            1. HTML 폼 내부에 있는 버튼은 기본적으로 type="submit"으로 취급됩니다. <= 크로스 브라우징 이슈 있음.
            2. 폼 내의 input 필드에서 Enter 키를 누르면, 브라우저는 submit 타입의 버튼을 찾아 클릭 이벤트를 발생시킵니다. <= 🔥
            3. type="button"으로 지정된 버튼은 폼 제출과 무관한 일반 버튼으로 취급됩니다.
            4. removeButton에 type="button"을 추가함으로써, 이 버튼이 폼 제출과 관련없는 일반 버튼임을 명시했습니다.
             */

            const removeButton = document.createElement("button");
            removeButton.innerHTML = "X";
            removeButton.type = "button";
            removeButton.className =
              "absolute top-0 right-0 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center cursor-pointer";
            removeButton.onclick = function () {
              container.remove();

              const data_transfer = new DataTransfer();

              Array.from(inputEl.files)
                .filter((file) => file.name !== currentFile.name)
                .forEach((file) => {
                  data_transfer.items.add(file);
                });

              inputEl.files = data_transfer.files;
            };
            container.appendChild(removeButton);

            previewDisplayEl.appendChild(container);

            resolve();
          };
          reader.readAsDataURL(currentFile);
        });
      });

      await Promise.all(promises);
    }
  }
}
