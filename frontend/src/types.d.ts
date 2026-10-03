declare module "plotly.js-basic-dist-min" {
  // The bundle ships no typings; only the small API surface used by the card is declared.
  const Plotly: {
    react(
      root: HTMLElement,
      data: unknown[],
      layout?: unknown,
      config?: unknown,
    ): Promise<unknown>;
    purge(root: HTMLElement): void;
    Plots: { resize(root: HTMLElement): void };
  };
  export default Plotly;
}
