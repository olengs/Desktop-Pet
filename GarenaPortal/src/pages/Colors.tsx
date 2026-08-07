const shades: { name: string; hex: string; swatch: string; lightText?: boolean }[] = [
  { name: 'garena-50', hex: '#feecec', swatch: 'bg-garena-50', lightText: true },
  { name: 'garena-100', hex: '#fdd3d4', swatch: 'bg-garena-100', lightText: true },
  { name: 'garena-200', hex: '#faa9ab', swatch: 'bg-garena-200', lightText: true },
  { name: 'garena-300', hex: '#f67e81', swatch: 'bg-garena-300', lightText: true },
  { name: 'garena-400', hex: '#ef5458', swatch: 'bg-garena-400' },
  { name: 'garena-500', hex: '#e93337', swatch: 'bg-garena-500' },
  { name: 'garena-600', hex: '#e41e26', swatch: 'bg-garena-600' },
  { name: 'garena-700', hex: '#d43831', swatch: 'bg-garena-700' },
  { name: 'garena-800', hex: '#b02e29', swatch: 'bg-garena-800' },
  { name: 'garena-900', hex: '#7e211e', swatch: 'bg-garena-900' },
  { name: 'garena-950', hex: '#451210', swatch: 'bg-garena-950' },
  { name: 'garena-ink', hex: '#16181a', swatch: 'bg-garena-ink' },
]

const semanticTokens = [
  { name: '--accent', description: 'Buttons, links, active nav state' },
  { name: '--accent-bg', description: 'Subtle accent backgrounds' },
  { name: '--accent-border', description: 'Accent borders / focus rings' },
  { name: '--text', description: 'Body text' },
  { name: '--text-h', description: 'Headings' },
  { name: '--bg', description: 'Page background' },
  { name: '--border', description: 'Dividers, card borders' },
]

function Colors() {
  return (
    <section className="mx-auto w-full max-w-4xl px-6 py-12 text-left">
      <h1>Color theme</h1>
      <p style={{ color: 'var(--text)' }}>
        The Garena brand red, sampled from garena.sg's compiled CSS, and the
        shades generated from it. Defined in{' '}
        <code>src/index.css</code> as a Tailwind <code>@theme</code>.
      </p>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
        {shades.map((shade) => (
          <div
            key={shade.name}
            className="overflow-hidden rounded-lg border"
            style={{ borderColor: 'var(--border)' }}
          >
            <div
              className={`${shade.swatch} flex h-20 items-end p-2 font-mono text-xs ${
                shade.lightText ? 'text-black/70' : 'text-white/90'
              }`}
            >
              {shade.name}
            </div>
            <div className="p-2 font-mono text-xs" style={{ color: 'var(--text)' }}>
              {shade.hex}
            </div>
          </div>
        ))}
      </div>

      <h2 className="mt-12">Semantic tokens</h2>
      <p style={{ color: 'var(--text)' }}>
        These CSS variables map onto the palette above and flip automatically
        with light/dark mode.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {semanticTokens.map((token) => (
          <div
            key={token.name}
            className="flex items-center gap-3 rounded-lg border p-3"
            style={{ borderColor: 'var(--border)' }}
          >
            <span
              className="h-8 w-8 shrink-0 rounded-full border"
              style={{ background: `var(${token.name})`, borderColor: 'var(--border)' }}
            />
            <div>
              <div className="font-mono text-sm" style={{ color: 'var(--text-h)' }}>
                {token.name}
              </div>
              <div className="text-xs" style={{ color: 'var(--text)' }}>
                {token.description}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default Colors
