module.exports = {
  content: ["./templates/**/*.html", "./**/*.py"],
  theme: { extend: {} },
  plugins: [require('@tailwindcss/line-clamp')],
}