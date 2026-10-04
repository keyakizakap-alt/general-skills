import { expect, mock, test } from 'claude-code/testing'

const PANE = { component: 'Pane', requestId: 'vibe-deck' } as const
const paneProps = (bodyColumns: number) =>
  ({ title: 'vibe-deck', isFocused: true, bodyColumns, placement: 'dock' }) as never

const bandProps = (bodyColumns: number) =>
  ({
    hasSurvey: false,
    isWorking: false,
    maxRows: 6,
    bodyColumns,
    scroll: { offset: 0, bodyRows: 5 },
    view: {},
  }) as never

test('/vibe switches theme and the gallery follows on every surface', async ($, on) => {
  mock.clock(on, { now: 1_000 })
  mock.store(on)
  on('ui.status', () => undefined)
  const ran = await $.command.run({ command: 'vibe', args: 'theme tokyo' })
  expect(ran.text).toContain('Tokyo Night')

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ plugin: 'vibe-deck', surface, ...PANE, props: paneProps(60) })
    if (surface === 'terminal') {
      expect((await ui.find({ key: 'use-tokyo' }))?.props.label).toBe('in use')
    }
    await ui.press({ key: 'use-ember' })
    expect((await ui.find({ key: 'use-tokyo' }))?.props.label).toBe('use')
    await ui.press({ key: 'use-rose' })
    expect((await ui.find({ key: 'use-rose' }))?.props.label).toBe('in use')
    await ui.press({ key: 'chat' })
    expect((await ui.find({ key: 'chat' }))?.props.label).toBe('chat style off')
    await ui.press({ key: 'chat' })
    await ui.unmount()
  }
})

test('unknown theme gives help, band shows counters after reset', async ($, on) => {
  mock.clock(on, { now: 1_000 })
  mock.store(on)
  on('ui.status', () => undefined)
  const bad = await $.command.run({ command: 'vibe', args: 'theme neon' })
  expect(bad.text).toContain('Unknown theme')

  await $.command.run({ command: 'vibe', args: 'reset' })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({
      plugin: 'vibe-deck',
      surface,
      component: 'AbovePrompt',
      props: bandProps(120),
    })
    expect(await ui.find({ type: 'Text', text: /VIBE/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /0 turns/ })).toBeDefined()
    await ui.unmount()
  }
})
