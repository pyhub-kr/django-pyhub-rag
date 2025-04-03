function markdownToHtml(text) {
    if (window.showdown?.Converter) {
        window.showdownConverter ||= new window.showdown.Converter({tables: true});
        return window.showdownConverter.makeHtml(text);
    } else {
        console.error('showdown library not found. Markdown to HTML conversion failed.');
        return text;
    }
}
