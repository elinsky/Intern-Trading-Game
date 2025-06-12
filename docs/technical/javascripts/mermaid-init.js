// Initialize Mermaid when the DOM is loaded
// This works with MkDocs Material's instant loading feature
document$.subscribe(function() {
  // Configure Mermaid with theme-aware settings
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    themeVariables: {
      // Use CSS variables from Material theme for consistency
      primaryColor: '#ff6b35',
      primaryTextColor: '#fff',
      primaryBorderColor: '#ff6b35',
      lineColor: '#333',
      secondaryColor: '#006064',
      tertiaryColor: '#fff',
      background: '#fff',
      mainBkg: '#fff',
      secondBkg: '#f5f5f5',
      tertiaryBkg: '#e8e8e8',
      primaryBorderColor: '#ff6b35',
      secondaryBorderColor: '#006064',
      tertiaryBorderColor: '#333',
      noteBkgColor: '#fff5ad',
      noteTextColor: '#333',
      darkMode: false,
      // Graph specific styling
      fontSize: '16px',
      fontFamily: '"Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif'
    },
    securityLevel: 'loose',
    logLevel: 'error'
  });

  // Re-render Mermaid diagrams after navigation
  mermaid.contentLoaded();
});

// Handle dark mode theme switching
const observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.type === 'attributes' && mutation.attributeName === 'data-md-color-scheme') {
      const isDark = document.body.getAttribute('data-md-color-scheme') === 'slate';

      mermaid.initialize({
        startOnLoad: false,
        theme: isDark ? 'dark' : 'default',
        themeVariables: {
          primaryColor: '#ff6b35',
          primaryTextColor: isDark ? '#fff' : '#333',
          primaryBorderColor: '#ff6b35',
          lineColor: isDark ? '#ccc' : '#333',
          secondaryColor: '#006064',
          tertiaryColor: isDark ? '#333' : '#fff',
          background: isDark ? '#1e1e1e' : '#fff',
          mainBkg: isDark ? '#1e1e1e' : '#fff',
          secondBkg: isDark ? '#2d2d2d' : '#f5f5f5',
          darkMode: isDark,
          fontSize: '16px',
          fontFamily: '"Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif'
        }
      });

      // Re-render all diagrams with new theme
      mermaid.contentLoaded();
    }
  });
});

// Start observing theme changes
if (document.body) {
  observer.observe(document.body, {
    attributes: true,
    attributeFilter: ['data-md-color-scheme']
  });
}
