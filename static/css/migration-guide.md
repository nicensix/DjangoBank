# Bootstrap 5 CSS Migration Guide

## Overview
This guide explains how to migrate from the old custom CSS (`style.css`) to the new Bootstrap 5 compatible utilities (`bootstrap-utilities.css`).

## Key Changes

### 1. CSS Custom Properties
The new system uses CSS custom properties for consistent theming:
- `--banking-primary`: Primary brand color
- `--banking-success`: Success/deposit color
- `--banking-danger`: Error/withdrawal color
- `--banking-warning`: Warning/transfer color
- `--banking-border-radius`: Standard border radius
- `--banking-shadow`: Standard shadow

### 2. Bootstrap Utility Classes to Use Instead of Custom CSS

#### Old Custom Classes → New Bootstrap Classes

| Old Custom Class | New Bootstrap Classes |
|------------------|----------------------|
| `.jumbotron` | `.bg-primary .text-white .p-5 .rounded-banking` |
| `.dashboard-card` | `.card .bg-success .text-white .shadow-banking` |
| `.transaction-item` | `.card .mb-3 .status-deposit/.status-withdrawal/.status-transfer` |
| `.feature-card` | `.card .text-center .p-4 .h-100 .shadow-banking-sm` |
| `.balance-display` | `.display-3 .fw-bold` |
| `.glass-effect` | `.glass-effect` (kept as utility) |
| `.text-gradient` | `.text-primary .fw-bold` |

#### Button Classes
Replace custom button styles with Bootstrap 5 classes:
- `.btn-primary .btn-hover-lift` for primary actions
- `.btn-success .btn-hover-lift` for positive actions
- `.btn-warning .btn-hover-lift` for caution actions
- `.btn-danger .btn-hover-lift` for critical actions

#### Form Classes
Use Bootstrap 5 form classes:
- `.form-floating` for floating labels
- `.form-control .focus-ring-banking` for inputs
- `.is-valid` and `.is-invalid` for validation states

#### Card Classes
Replace custom card styles:
- `.card .shadow-banking` for standard cards
- `.card .shadow-banking-lg` for prominent cards
- `.card .rounded-banking` for custom border radius

#### Spacing and Layout
Use Bootstrap 5 spacing utilities:
- `m-*` and `p-*` for margins and padding
- `g-*` for gutters in grid systems
- `gap-*` for flexbox gaps

### 3. Animation Classes

#### Page Transitions
- Add `.page-transition` to main content containers

#### Alert Animations
- Add `.alert-animated` to alert components

#### Button Hover Effects
- Add `.btn-hover-lift` to buttons for subtle hover animation

### 4. Responsive Design

#### Mobile Navigation
- Use `.navbar-collapse-enhanced` for mobile navigation styling
- Add `.nav-link-mobile` to navigation links in mobile view

#### Breakpoint Classes
Use Bootstrap 5 responsive classes:
- `col-12 col-md-6 col-lg-4` for responsive columns
- `d-none d-md-block` for responsive visibility
- `fs-6 fs-md-5 fs-lg-4` for responsive typography

### 5. Accessibility Improvements

#### Focus Management
- Use `.focus-ring-banking` for custom focus indicators
- Add `.visually-hidden-focusable` for skip links

#### Screen Reader Support
- Use `.visually-hidden` for screen reader only content
- Ensure proper ARIA labels and semantic HTML

### 6. Performance Optimizations

#### Reduced Custom CSS
The new system minimizes custom CSS in favor of Bootstrap utilities:
- Smaller CSS file size
- Better caching with Bootstrap CDN
- Consistent design system

#### Loading States
- Use `.btn-loading` class for button loading states
- Implement with JavaScript: `button.classList.add('btn-loading')`

### 7. Dark Mode Support
The new system includes automatic dark mode support:
- Respects `prefers-color-scheme: dark`
- Automatic color adjustments for shadows and glass effects

### 8. Print Styles
Enhanced print styles:
- Hides navigation and interactive elements
- Optimizes layout for printing
- Maintains readability

## Implementation Steps

1. **Replace CSS file reference** in base template:
   ```html
   <!-- Old -->
   <link rel="stylesheet" href="{% static 'css/style.css' %}">
   
   <!-- New -->
   <link rel="stylesheet" href="{% static 'css/bootstrap-utilities.css' %}">
   ```

2. **Update HTML classes** in templates using the migration table above

3. **Test responsive behavior** across different screen sizes

4. **Verify accessibility** with screen readers and keyboard navigation

5. **Check print styles** by testing print preview

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Notes
- The old `style.css` file should be kept as backup until migration is complete
- Some complex animations may need JavaScript for full functionality
- Test thoroughly on all supported devices and browsers