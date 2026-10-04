import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Prefs, Stats, ThemeId } from '../types'

// Palettes from each project's official palette files (Catppuccin, Tokyo Night,
// Rosé Pine). "ember" is this mod's own warm palette.
type Palette = {
  label: string
  tagline: string
  base: string
  surface: string
  text: string
  muted: string
  accent: string
  accent2: string
  ok: string
  warn: string
  err: string
  info: string
}

const THEMES: Record<ThemeId, Palette> = {
  mocha: {
    label: 'Catppuccin Mocha',
    tagline: 'soft pastel, cozy late-night',
    base: '#1e1e2e',
    surface: '#313244',
    text: '#cdd6f4',
    muted: '#6c7086',
    accent: '#cba6f7',
    accent2: '#89b4fa',
    ok: '#a6e3a1',
    warn: '#f9e2af',
    err: '#f38ba8',
    info: '#94e2d5',
  },
  tokyo: {
    label: 'Tokyo Night',
    tagline: 'deep navy, neon accents',
    base: '#1a1b26',
    surface: '#292e42',
    text: '#c0caf5',
    muted: '#565f89',
    accent: '#7aa2f7',
    accent2: '#bb9af7',
    ok: '#9ece6a',
    warn: '#e0af68',
    err: '#f7768e',
    info: '#7dcfff',
  },
  rose: {
    label: 'Rosé Pine',
    tagline: 'muted, warm, low blue light',
    base: '#191724',
    surface: '#26233a',
    text: '#e0def4',
    muted: '#6e6a86',
    accent: '#ebbcba',
    accent2: '#c4a7e7',
    ok: '#9ccfd8',
    warn: '#f6c177',
    err: '#eb6f92',
    info: '#31748f',
  },
  ember: {
    label: 'Ember',
    tagline: 'warm stone and amber, focus mode',
    base: '#1c1917',
    surface: '#292524',
    text: '#e7e5e4',
    muted: '#78716c',
    accent: '#fb923c',
    accent2: '#fbbf24',
    ok: '#a3e635',
    warn: '#facc15',
    err: '#f87171',
    info: '#38bdf8',
  },
  latte: {
    label: 'Catppuccin Latte',
    tagline: 'light terminals, daytime',
    base: '#eff1f5',
    surface: '#ccd0da',
    text: '#4c4f69',
    muted: '#9ca0b0',
    accent: '#8839ef',
    accent2: '#1e66f5',
    ok: '#40a02b',
    warn: '#df8e1d',
    err: '#d20f39',
    info: '#179299',
  },
}

const ORDER: ThemeId[] = ['mocha', 'tokyo', 'rose', 'ember', 'latte']
const DEFAULT_PREFS: Prefs = { band: true, chat: true, prompts: true }
const EDIT_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit'])
const PANE = 'vibe-deck'

const theme = atom({ plugin: 'vibe-deck', key: 'theme' } as const, 'mocha')
const prefs = atom({ plugin: 'vibe-deck', key: 'prefs' } as const, DEFAULT_PREFS)
const stats = atom({ plugin: 'vibe-deck', key: 'stats' } as const, null)
const now = atom({ plugin: 'vibe-deck', key: 'now' } as const, 0)

const CHAT_STYLE = [
  'Answer formatting (vibe-deck mod, chosen by the user):',
  "- Write in the user's language.",
  '- Open with the conclusion in one bold line, then the reasons and details.',
  '- Use short `##` headings only when the answer has several parts; keep paragraphs to 2-3 sentences.',
  '- Prefer tight bullet lists (at most ~6 items) and a table when comparing options.',
  '- Mark status with ✅ done, ⚠️ caution, ❌ failed, sparingly and only where it adds meaning.',
  '- When work remains, end with one line starting "Next →" naming the next concrete step.',
  '- No filler openers or closers; whitespace over walls of text.',
].join('\n')

const isThemeId = (value: unknown): value is ThemeId =>
  typeof value === 'string' && value in THEMES

const fmtDuration = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${String(s % 60).padStart(2, '0')}s`
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`
}

const fmtElapsed = (ms: number) => {
  const m = Math.max(0, Math.floor(ms / 60000))
  return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}`
}

const HELP = [
  '/vibe               open the theme gallery',
  `/vibe theme <id>    switch theme (${ORDER.join(', ')})`,
  '/vibe next          cycle to the next theme',
  '/vibe band on|off   the HUD band above the prompt',
  '/vibe chat on|off   the tidy answer style for replies',
  '/vibe prompts on|off  the styled rows for your prompts',
  '/vibe reset         reset session counters',
].join('\n')

async function setTheme($: EngineInterface, id: ThemeId) {
  await update($, theme, () => id)
  await $.store.set('theme', id)
  $.ui.status(`◆ ${THEMES[id].label}`)
}

async function setPref($: EngineInterface, key: keyof Prefs, value: boolean) {
  const next = await update($, prefs, p => ({ ...p, [key]: value }))
  await $.store.set('prefs', next)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const saved = await $.store.get('theme')
    const savedPrefs = (await $.store.get('prefs')) as Partial<Prefs> | undefined
    if (isThemeId(saved)) await update($, theme, () => saved)
    if (savedPrefs) await update($, prefs, () => ({ ...DEFAULT_PREFS, ...savedPrefs }))

    const t = await $.clock.now()
    await update($, now, () => t)
    // Counters live in $.state, so a hot reload keeps them.
    await update($, stats, s =>
      s ?? { startedAt: t, turns: 0, tools: 0, edits: 0, turnStartedAt: 0, lastTurnMs: null },
    )
    $.clock.every(30_000, () => {
      void $.clock.now().then(n => update($, now, () => n))
    })

    $.ui.status(`◆ ${THEMES[await read($, theme)].label}`)
    await $.command.register({
      name: 'vibe',
      description: 'vibe-deck: theme gallery, HUD band and chat style',
    })

    return next(e)
  })

  on('command.run', { command: 'vibe' }, async ($, e) => {
    const [verb = '', arg = ''] = e.args.trim().toLowerCase().split(/\s+/)

    if (verb === '') {
      await $.ui.open({ id: PANE, title: 'vibe-deck' })
      return { text: '◆ vibe-deck gallery opened (1-5 theme, b/c/p toggles).' }
    }
    if (verb === 'theme' || verb === 'next') {
      const current = await read($, theme)
      const id = verb === 'next' ? ORDER[(ORDER.indexOf(current) + 1) % ORDER.length] : arg
      if (!isThemeId(id)) return { text: `Unknown theme "${arg}". Themes: ${ORDER.join(', ')}` }
      await setTheme($, id)
      return { text: `◆ Theme: ${THEMES[id].label} — ${THEMES[id].tagline}` }
    }
    if ((verb === 'band' || verb === 'chat' || verb === 'prompts') && (arg === 'on' || arg === 'off')) {
      await setPref($, verb, arg === 'on')
      return { text: `◆ ${verb}: ${arg}` }
    }
    if (verb === 'reset') {
      const t = await $.clock.now()
      await update($, stats, () => ({
        startedAt: t, turns: 0, tools: 0, edits: 0, turnStartedAt: 0, lastTurnMs: null,
      }))
      return { text: '◆ Session counters reset.' }
    }
    return { text: HELP }
  })

  on('prompt.submit', async ($, e, next) => {
    const t = await $.clock.now()
    await update($, stats, s => (s ? { ...s, turnStartedAt: t } : s))

    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const isEdit = EDIT_TOOLS.has(String(e.tool))
    await update($, stats, s =>
      s ? { ...s, tools: s.tools + 1, edits: s.edits + (isEdit ? 1 : 0) } : s,
    )

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const t = await $.clock.now()
    const s = await update($, stats, s =>
      s && s.turnStartedAt > 0
        ? { ...s, turns: s.turns + 1, lastTurnMs: t - s.turnStartedAt, turnStartedAt: 0 }
        : s,
    )
    if (s?.lastTurnMs != null && s.lastTurnMs > 90_000) {
      $.ui.toast(`✦ Done in ${fmtDuration(s.lastTurnMs)}`)
    }

    return next(e)
  })

  on('prompt.compose', async ($, e, next) => {
    const result = await next(e)
    if (!(await read($, prefs)).chat) return result

    return {
      sections: [
        ...result.sections,
        { id: 'vibe-deck:chat-style', text: CHAT_STYLE, scope: 'session' as const },
      ],
    }
  })

  on('ui.render', { component: 'UserMessage' }, async ($, e, next) => {
    if (e.props.isExpanded || e.props.origin.kind !== 'composer') return next(e)
    if (!(await read($, prefs)).prompts) return next(e)

    const p = THEMES[await read($, theme)]
    const { Box, Text } = $.ui.resolve(e)

    return (
      <Box flexDirection="row" marginTop={1}>
        <Text color={p.accent} bold>
          {'▍ '}
        </Text>
        <Text color={p.text}>{e.props.text}</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const pr = await read($, prefs)
    const s = await read($, stats)
    if (e.props.hasSurvey || !pr.band || s === null) return next(e)

    const p = THEMES[await read($, theme)]
    const t = await read($, now)
    const cols = e.props.bodyColumns
    const { Box, Text } = $.ui.resolve(e)

    const segments: { glyph: string; value: string; color: string }[] = [
      e.props.isWorking
        ? { glyph: '●', value: 'working', color: p.warn }
        : { glyph: '○', value: 'ready', color: p.ok },
      { glyph: '⏱', value: fmtElapsed(t - s.startedAt), color: p.info },
      { glyph: '↻', value: `${s.turns} turns`, color: p.accent2 },
      { glyph: '⚒', value: `${s.tools} tools`, color: p.accent },
      { glyph: '✎', value: `${s.edits} edits`, color: p.ok },
    ]
    if (s.lastTurnMs !== null) {
      segments.push({ glyph: '⚡', value: `last ${fmtDuration(s.lastTurnMs)}`, color: p.warn })
    }
    const fit = cols < 60 ? 2 : cols < 90 ? 4 : segments.length

    return (
      <Box flexDirection="row">
        <Text backgroundColor={p.accent} color={p.base} bold>
          {' ◆ VIBE '}
        </Text>
        {segments.slice(0, fit).map((seg, i) => (
          <Text key={String(i)} wrap="truncate">
            <Text color={p.muted}>{i === 0 ? '  ' : '  │  '}</Text>
            <Text color={seg.color}>{seg.glyph} </Text>
            <Text color={p.text}>{seg.value}</Text>
          </Text>
        ))}
        {cols >= 110 && <Text color={p.muted}>{'   /vibe'}</Text>}
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const current = await read($, theme)
    const pr = await read($, prefs)
    const p = THEMES[current]
    const { Box, Text, Button } = $.ui.resolve(e)
    const swatchKeys = ['accent', 'accent2', 'ok', 'warn', 'err', 'info'] as const

    return (
      <Box flexDirection="column" gap={1}>
        <Text color={p.accent} bold>
          ◆ vibe-deck · themes
        </Text>
        {ORDER.map((id, i) => {
          const t = THEMES[id]
          const isOn = id === current
          return (
            <Box key={`row-${id}`} flexDirection="column">
              <Box flexDirection="row" gap={1}>
                <Text color={isOn ? t.accent : p.muted}>{isOn ? '●' : '○'}</Text>
                <Text>
                  {swatchKeys.map(k => (
                    <Text backgroundColor={t[k]}>{'  '}</Text>
                  ))}
                </Text>
                <Text color={isOn ? p.text : p.muted} bold={isOn}>
                  {t.label}
                </Text>
                <Button
                  key={`use-${id}`}
                  label={isOn ? 'in use' : 'use'}
                  hotkey={String(i + 1)}
                  variant={isOn ? 'primary' : 'secondary'}
                  onPress={() => setTheme($, id)}
                />
              </Box>
              <Text color={p.muted}>{`    ${t.tagline}`}</Text>
            </Box>
          )
        })}
        <Text color={p.muted}>{'─'.repeat(Math.max(8, Math.min(48, e.props.bodyColumns)))}</Text>
        <Box flexDirection="row" gap={2} flexWrap="wrap">
          <Button
            key="band"
            label={`band ${pr.band ? 'on' : 'off'}`}
            hotkey="b"
            onPress={() => setPref($, 'band', !pr.band)}
          />
          <Button
            key="chat"
            label={`chat style ${pr.chat ? 'on' : 'off'}`}
            hotkey="c"
            onPress={() => setPref($, 'chat', !pr.chat)}
          />
          <Button
            key="prompts"
            label={`prompt rows ${pr.prompts ? 'on' : 'off'}`}
            hotkey="p"
            onPress={() => setPref($, 'prompts', !pr.prompts)}
          />
        </Box>
        <Text color={p.muted}>1-5 theme · b/c/p toggle · Esc back to prompt</Text>
      </Box>
    )
  })
}
