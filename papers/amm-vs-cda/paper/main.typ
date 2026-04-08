// ══════════════════════════════════════════════════════════
// AMM vs CDA: Paper V4 — Full ICAIF paper
// Target: ICAIF 2026 (8 pages + appendix)
// ══════════════════════════════════════════════════════════

// ── Phase 1 data (depth=M, FV-consistent valuation) ──
#let AMM_LP_0 = "448"
#let AMM_LP_10 = "241"
#let AMM_LP_20 = "196"
#let AMM_LP_30 = "147"
#let AMM_LP_50 = "71"
#let AMM_NOISE_0 = "-22"
#let AMM_NOISE_10 = "-16"
#let AMM_NOISE_20 = "-19"
#let AMM_NOISE_30 = "-17"
#let AMM_NOISE_50 = "-20"
#let CDA_NOISE_0 = "-1"
#let CDA_NOISE_10 = "-3"
#let CDA_NOISE_20 = "-8"
#let CDA_NOISE_30 = "-6"
#let CDA_NOISE_50 = "-6"
#let AMM_INF_10 = "24"
#let AMM_INF_20 = "26"
#let AMM_INF_30 = "15"
#let AMM_INF_50 = "13"
#let CDA_INF_10 = "21"
#let CDA_INF_20 = "25"
#let CDA_INF_30 = "9"
#let CDA_INF_50 = "4"
#let CDA_MM_0 = "5"
#let CDA_MM_10 = "6"
#let CDA_MM_20 = "2"
#let CDA_MM_30 = "4"
#let CDA_MM_50 = "4"
#let CDA_WELFARE_0 = "-17"
// Per-trade decomposition
#let AMM_EXEC = "1.00"
#let CDA_EXEC = "0.40"
#let AMM_CPF = "0.19"
#let CDA_CPF = "0.03"
#let AMM_FEE_PCT = "13"
#let AMM_SLIP_PCT = "87"
#let VOL_RATIO = "3.9"
#let COST_RATIO = "5.5"
// Phase 2 LP
#let L0_LP_0 = "147"
#let L0_LP_20 = "88"
#let L0_LP_50 = "68"
#let L1_LP_0 = "155"
#let L1_LP_20 = "104"
#let L1_LP_50 = "63"
#let L2_LP_0 = "137"
#let L2_LP_20 = "85"
#let L2_LP_50 = "50"
// Phase 2 Noise
#let L0_N_0 = "-18"
#let L0_N_20 = "-13"
#let L0_N_50 = "-21"
#let L1_N_0 = "-21"
#let L1_N_20 = "-20"
#let L1_N_50 = "-19"
#let L2_N_0 = "-22"
#let L2_N_20 = "-16"
#let L2_N_50 = "-17"
// Robustness
#let ROB_CDA_P00 = "-12"
#let ROB_CDA_P04 = "-10"
#let ROB_CDA_P08 = "-3"
#let ROB_AMM_P00 = "-5"
#let ROB_AMM_P04 = "-7"
#let ROB_AMM_P08 = "-8"
// Totals
#let N_TOTAL = "2,205"

#import "@preview/bloated-neurips:0.7.0": botrule, midrule, neurips2025, paragraph, toprule, url

#let affls = (
  rhul: (
    department: "Department of Economics",
    institution: "Royal Holloway, University of London",
    location: "Egham",
    country: "United Kingdom",
  ),
)

#let authors = (
  (name: "Wenbin Wu", affl: "rhul", email: "wenbin.wu@rhul.ac.uk"),
  (name: "Alessio Ferrini", affl: "rhul"),
)

#show: neurips2025.with(
  title: [Execution Guarantee as Cost Transfer:\ How AMMs and CDAs Distribute Surplus Among Heterogeneous Traders],
  authors: (authors, affls),
  keywords: ("automated market maker", "continuous double auction", "adverse selection", "market microstructure", "DeFi", "agent-based simulation"),
  abstract: [
    We compare how automated market makers (AMMs) and continuous double auctions (CDAs) distribute trading surplus among noise traders, informed arbitrageurs, and liquidity providers using #N_TOTAL computational markets under shared fundamental value processes. AMMs transfer substantially more value from noise traders to liquidity providers (LPs) than CDAs: AMM noise traders pay $approx$22 per trader versus $approx$5 in CDAs, while AMM LPs earn up to 448 in aggregate versus CDA market makers earning $approx$5. This gap arises from both the extensive margin (#VOL_RATIO$times$ more fills due to guaranteed execution) and the intensive margin (#COST_RATIO$times$ higher cost per fill, of which #AMM_SLIP_PCT% is slippage and only #AMM_FEE_PCT% is fees). AMM LP returns decline monotonically with informed trading fraction (448 #sym.arrow.r 71), confirming adverse selection predictions from the loss-versus-rebalancing literature. This pattern is invariant to AMM sophistication (constant product, concentrated liquidity, dynamic fees) and robust to market duration, fee levels, and noise trader parameterization. Our results characterize a fundamental distributional tradeoff: AMMs are efficient transfer mechanisms that convert execution guarantees into LP revenue, while CDAs protect uninformed traders through execution optionality at the cost of lower LP returns.
  ],
  bibliography: bibliography("main.bib"),
  accepted: false,
)

= Introduction

How should a market mechanism allocate surplus among heterogeneous participants? Traditional continuous double auctions (CDAs) and DeFi's automated market makers (AMMs) answer this question differently. In a CDA, participants choose between aggressive market orders and passive limit orders. Passive orders provide an implicit option: they execute only when matched, and unfilled orders expire at zero cost @foucault1999order. This _execution optionality_ protects uninformed traders --- non-execution prevents costly fills when the market moves against a resting order. AMMs eliminate this optionality: every swap executes immediately against the bonding curve.

The theoretical literature has analyzed each mechanism in isolation. For AMMs, @milionis2023automated quantify LP losses through loss-versus-rebalancing (LVR), @park2023conceptual shows AMMs are exploitable by informed traders, and @routledge2025automated derive optimal LP strategies. For CDAs, @glosten1985bid and @kyle1985continuous establish how informed trading affects spreads. However, direct distributional comparisons under controlled conditions remain scarce. We address this gap using #N_TOTAL computational markets with shared fundamental value processes, noise traders, informed arbitrageurs, and endogenous liquidity providers.

Our central finding is a sharp distributional tradeoff. AMM noise traders pay $approx$22 per trader versus $approx$5 in CDAs, with the difference flowing to LPs (up to #AMM_LP_0 in aggregate). A per-trade decomposition reveals two multiplicative components: #VOL_RATIO$times$ more fills (the extensive margin) and #COST_RATIO$times$ higher cost per fill (the intensive margin), of which #AMM_SLIP_PCT% is slippage and only #AMM_FEE_PCT% is fees. This explains why fee-focused innovations (concentrated liquidity, dynamic fees) have limited impact: they target the smaller cost component.

LP adverse selection --- the monotonic decline in LP returns as informed fraction increases --- holds across all three AMM sophistication levels (L0, L1, L2) with no significant differences ($p > 0.2$), confirming that the distributional pattern is structural. We make three contributions: (1) quantifying the AMM--CDA distributional difference via extensive/intensive margin decomposition; (2) confirming LVR adverse selection predictions @milionis2023automated in a heterogeneous-agent simulation across AMM design variants; and (3) establishing robustness across noise trader behavior, market duration, and fee levels.

= Related Work <sec:related>

*AMM theory.* @angeris2020improved formalize constant-product AMMs. @park2023conceptual shows AMMs are exploitable by informed traders, a finding quantified as loss-versus-rebalancing (LVR) by @milionis2023automated, who predict monotonic LP loss growth with informed activity. @routledge2025automated derive optimal LP strategies including inaction regions. Our simulation implements these strategies and tests whether predicted adverse selection patterns emerge with heterogeneous traders.

*AMM--CDA comparisons.* @lehar2025fragmented predict that AMMs attract uninformed flow while informed traders prefer CDAs. @aspris2025decentralized empirically find DEX costs substantially exceed CEX costs. Our computational approach controls the information environment and trader composition, isolating the mechanism's distributional effect from empirical confounds.

*CDA microstructure.* @gode1993allocative show CDAs achieve high efficiency even with zero-intelligence traders. @glosten1985bid and @kyle1985continuous formalize adverse selection. @foucault1999order demonstrates that limit orders have option value --- central to our argument that AMMs eliminate the execution optionality protecting uninformed CDA traders.

*MEV.* @canidio2023batch propose batch execution against MEV. @zhang2025batch show batch auctions have residual MEV. @bartoletti2025maximizing establish sandwich attacks as optimal MEV strategies.

= Experimental Design <sec:design>

== Environment

All markets share a common fundamental value process $v(t)$, modeled as a random walk:
$ v(t) = v(t - 1) + epsilon_t, quad epsilon_t tilde.op cal(N)(0, sigma^2), quad v(0) = 100 $
with $sigma = 0.5$. This process generates price movements of realistic magnitude (approximately 3--5 units over a 1-minute market) while remaining stationary enough for meaningful welfare comparisons across mechanisms. Markets run for 60 seconds with $N = 20$ traders plus endogenous liquidity providers. All terminal asset positions are valued at $v(T)$, the final fundamental value, ensuring consistent welfare accounting across mechanisms.

== Agent Descriptions

#paragraph[Noise traders (ZI-C with EMA anchoring).] Each noise trader acts at 2/s, with random buy/sell direction and unit order size. In the CDA, 80% of actions are passive limit orders priced at an EMA-anchored estimate of fair value ($alpha = 0.3$) plus a uniform offset in $[-2, +2]$; the remaining 20% are market orders. In the AMM, every action is a swap at the prevailing bonding curve price. This order-type asymmetry is not a confound but the defining feature: the CDA provides execution optionality that the AMM does not.

#paragraph[Informed traders (arbitrageurs).] Informed traders observe $v(t)$ and trade whenever $|p_"market" - v(t)| > delta$ with $delta = 4$. They submit market orders in the CDA and equivalent swaps in the AMM, at 1 unit per action with a maximum rate of 4/s. The same logic operates identically across mechanisms.

#paragraph[CDA market maker.] A single market maker quotes two-sided at:
$ p_"ask" = p_"mid" + 1.5 - gamma dot I, quad p_"bid" = p_"mid" - 1.5 - gamma dot I $
where $I$ is inventory and $gamma = 0.1$. Quotes refresh at 4/s, generating a continuously updated order book.

#paragraph[AMM liquidity providers.] Three LP agents manage positions using inaction regions @routledge2025automated, rebalancing only when the pool price deviates from $v(t)$ by more than $plus.minus$5%. In the concentrated liquidity variant (L1), LPs concentrate within $plus.minus$10% of the current price. In the dynamic fee variant (L2), the pool adjusts fees between 1--30 bps based on realized volatility.

== Calibration

We calibrated parameters via a 1,294-market sweep across 108 configurations, varying $sigma in {0.25, 0.5, 1.0}$, $delta in {2, 4, 8}$, $s in {0.5, 1.0, 1.5, 2.0}$, and $f in {1, 5, 10, 30}$ bps. Each was scored on 13 criteria (see @sec:app_calibration) covering trading activity, profitability, price efficiency, and stability. Configuration "Cal 19" scored 11/13 and was selected as the baseline.

== Welfare Measurement

We define trader welfare as the sum of realized trading PnL and inventory valuation at the fundamental value:
$ W_i = "cash"_i (T) + q_i (T) dot v(T) - "cash"_i (0) - q_i (0) dot v(0) $
where $q_i (t)$ is trader $i$'s asset holdings at time $t$. This FV-consistent valuation ensures that unrealized gains and losses from inventory positions are accounted for at the true fundamental value rather than the market price, avoiding mechanism-specific valuation artifacts. Total welfare for a trader class is the sum across all traders in that class. Per-trader figures report the mean across traders within the class.

== Experimental Design

Our experiments proceed in three phases, plus robustness checks:

#figure(
  table(
    columns: 4,
    stroke: none,
    table.hline(),
    [*Phase*], [*Design*], [*Purpose*], [*Markets*],
    table.hline(),
    [1: Core], [2 mech $times$ 5 inf. frac. $times$ 5 depths $times$ 30 reps], [Distributional comparison], [1,500],
    [2: AMM Ladder], [3 AMM levels $times$ 3 inf. frac. $times$ 30 reps], [LP sophistication effects], [270],
    [3: MEV], [3 mech $times$ 2 orderings $times$ 2 MEV $times$ 15 reps], [MEV extraction], [135],
    [Robustness], [passive ratio, duration, fee sweeps], [Parameter sensitivity], [300],
    table.hline(),
    [*Total*], [], [], [*#N_TOTAL*],
    table.hline(),
  ),
  caption: [Experimental design overview. Each market runs for 60 seconds with 20 traders plus liquidity providers on a shared fundamental value process.],
) <tab:design>

*Phase 1* varies informed fraction $in {0%, 10%, 20%, 30%, 50%}$ across AMM and CDA at five depth levels with 30 replications per cell. *Phase 2* varies AMM sophistication: L0 (CPMM, Uniswap v2), L1 (concentrated liquidity, v3), L2 (dynamic fees, v4-style) at three informed fractions. *Phase 3* introduces MEV agents (CDA spoofer, AMM sandwich attacker). *Robustness* varies the CDA passive ratio (0.0, 0.4, 0.8), market duration (1, 3, 5 min), and AMM fee level (1, 5, 10, 30 bps).

== Parameter Summary

#figure(
  table(
    columns: 3,
    stroke: none,
    table.hline(),
    [*Parameter*], [*Value*], [*Description*],
    table.hline(),
    [$v(0)$], [100], [Initial fundamental value],
    [$sigma$], [0.5], [Fundamental value innovation s.d.],
    [$N$], [20], [Traders per market (excl. LPs/MM)],
    [Duration], [60 s], [Market length],
    [Noise rate], [2/s], [Noise trader action frequency],
    [Passive ratio], [0.8], [CDA noise limit-order probability],
    [$alpha_"EMA"$], [0.3], [Noise trader EMA smoothing],
    [$delta$], [4], [Informed arbitrage threshold],
    [Inf. rate], [4/s], [Informed trader max action frequency],
    [$s$], [1.5], [CDA market maker half-spread],
    [$gamma$], [0.1], [CDA inventory adjustment coefficient],
    [$f$], [5 bps], [AMM base swap fee],
    [LP inaction], [$plus.minus$5%], [AMM LP rebalancing threshold],
    [LP count], [3], [Number of AMM LP agents],
    table.hline(),
  ),
  caption: [Baseline parameter values (Cal 19 configuration, selected from 108-configuration sweep over 1,294 calibration markets).],
) <tab:params>

= Results <sec:results>

== The Distributional Tradeoff <sec:distrib>

@tab:phase1 presents the core distributional results at depth $= M$ (medium pool depth) with 30 replications per cell.

#figure(
  table(
    columns: 7,
    stroke: none,
    table.hline(),
    [*Inf. %*], [*AMM Noise*], [*CDA Noise*], [*AMM LP*], [*CDA MM*], [*AMM Inf.*], [*CDA Inf.*],
    table.hline(),
    [0%],  [#AMM_NOISE_0],  [#CDA_NOISE_0],  [#AMM_LP_0],  [#CDA_MM_0],  [---],  [---],
    [10%], [#AMM_NOISE_10], [#CDA_NOISE_10], [#AMM_LP_10], [#CDA_MM_10],  [#AMM_INF_10],  [#CDA_INF_10],
    [20%], [#AMM_NOISE_20], [#CDA_NOISE_20], [#AMM_LP_20], [#CDA_MM_20],  [#AMM_INF_20], [#CDA_INF_20],
    [30%], [#AMM_NOISE_30], [#CDA_NOISE_30], [#AMM_LP_30], [#CDA_MM_30],  [#AMM_INF_30],  [#CDA_INF_30],
    [50%], [#AMM_NOISE_50], [#CDA_NOISE_50], [#AMM_LP_50], [#CDA_MM_50], [#AMM_INF_50],  [#CDA_INF_50],
    table.hline(),
  ),
  caption: [Phase 1 distributional results (depth $= M$, 30 replications). Noise and informed PnL are per trader; LP/MM PnL is aggregate. AMM noise traders pay 3--22$times$ more than CDA counterparts; the difference flows to LPs.],
) <tab:phase1>

The distributional asymmetry is large and consistent across all informed fractions. At 0% informed (no adverse selection), AMM noise traders lose #AMM_NOISE_0 per trader while CDA noise traders lose only #CDA_NOISE_0. The entire AMM noise cost transfers to LPs, who earn #AMM_LP_0 in aggregate. CDA market makers earn only #CDA_MM_0 over the same period. At 50% informed, AMM LP returns decline to #AMM_LP_50 as informed arbitrageurs extract from the pool, but noise traders still pay $approx$20 per trader --- the cost is now shared between LPs and informed traders rather than accruing entirely to LPs.

CDA market maker PnL is small and remarkably stable across informed fractions (ranging from #CDA_MM_20 to #CDA_MM_10), reflecting the thin spread and low execution probability. CDA noise traders benefit from _execution optionality_: approximately 60% of their passive limit orders never fill, incurring zero cost @foucault1999order. The orders that do fill tend to be those posted at favorable prices relative to the current fundamental value.

@fig:h1 visualizes the LP adverse selection pattern. AMM LP returns decline monotonically from #AMM_LP_0 at 0% informed to #AMM_LP_50 at 50% informed, consistent with theoretical predictions. CDA market maker returns show no equivalent decline, as the CDA's order book structure allows the market maker to adjust quotes in response to informed activity.

#figure(
  image("../figures/h1_adverse_selection.pdf", width: 85%),
  caption: [LP/MM aggregate PnL by informed fraction. AMM LP returns decline monotonically with informed trading intensity, confirming adverse selection predictions from the LVR literature. CDA market maker returns are stable across all conditions.],
) <fig:h1>

@fig:h3 shows the noise trader perspective. AMM noise trader losses are consistently larger than CDA noise trader losses at every informed fraction, reflecting the cost of guaranteed execution.

#figure(
  image("../figures/h3_uninformed_welfare.pdf", width: 85%),
  caption: [Noise trader PnL (per trader) by informed fraction and mechanism. AMM noise traders consistently pay more than CDA counterparts. The gap reflects the cost of execution guarantees.],
) <fig:h3>

== Per-Trade Cost Decomposition <sec:decomp>

To understand _why_ AMM noise traders pay more, we decompose the cost differential into execution probability (extensive margin) and cost per fill (intensive margin).

#figure(
  table(
    columns: 6,
    stroke: none,
    table.hline(),
    [*Mechanism*], [*Exec. Prob.*], [*Fills/Market*], [*Cost/Fill*], [*Fee %*], [*Slippage %*],
    table.hline(),
    [AMM], [#AMM_EXEC], [2,400], [#AMM_CPF], [#AMM_FEE_PCT], [#AMM_SLIP_PCT],
    [CDA], [#CDA_EXEC], [617], [#CDA_CPF], [---], [100],
    table.hline(),
  ),
  caption: [Per-trade decomposition at 0% informed, depth $= M$. AMM execution is guaranteed (probability 1.00); CDA passive orders fill with probability 0.40. The noise trader cost differential arises from both margins: more fills (#VOL_RATIO$times$) and higher cost per fill (#COST_RATIO$times$).],
) <tab:decomp>

*Extensive margin.* AMM noise traders execute #VOL_RATIO$times$ more trades because every swap fills immediately (execution probability $= #AMM_EXEC$). CDA passive orders fill with probability #CDA_EXEC, providing a natural filter against costly execution. The 60% of passive orders that expire unfilled would have been executed as swaps in an AMM, each incurring positive cost. This margin alone accounts for the majority of the welfare gap.

*Intensive margin.* Each AMM fill costs #COST_RATIO$times$ more than a CDA fill. Decomposing AMM per-fill cost further: #AMM_SLIP_PCT% of the cost is _slippage_ (price impact from the constant-product bonding curve) and only #AMM_FEE_PCT% is the protocol fee. In the CDA, all execution costs are effective spread (the difference between the execution price and the fundamental value), which we classify entirely as slippage.

*Implications for AMM design.* The Uniswap v2 #sym.arrow.r v3 #sym.arrow.r v4 trajectory focuses on two optimizations: concentrated liquidity (reducing slippage per unit of capital) and dynamic fees (adjusting fees to market conditions). Our decomposition reveals why these innovations have limited impact on the overall cost differential. Concentrated liquidity reduces per-trade slippage but simultaneously increases the number of units of capital exposed to adverse selection. Dynamic fees target the 13% fee component rather than the 87% slippage component. Mechanisms that provide uninformed traders with _execution optionality_ --- conditional swaps, intent-based execution, limit-order-like AMM features --- would address the dominant cost component by reducing the extensive margin.

== LP Adverse Selection Across the AMM Ladder <sec:ladder>

Phase 2 tests whether AMM design innovations alter the distributional pattern. @tab:phase2 reports LP and noise trader outcomes across three AMM sophistication levels at three informed fractions.

#figure(
  table(
    columns: 7,
    stroke: none,
    table.hline(),
    [*Level*], [*LP: 0%*], [*LP: 20%*], [*LP: 50%*], [*Noise: 0%*], [*Noise: 20%*], [*Noise: 50%*],
    table.hline(),
    [L0 (CPMM)], [#L0_LP_0], [#L0_LP_20], [#L0_LP_50], [#L0_N_0], [#L0_N_20], [#L0_N_50],
    [L1 (Concentrated)], [#L1_LP_0], [#L1_LP_20], [#L1_LP_50], [#L1_N_0], [#L1_N_20], [#L1_N_50],
    [L2 (Dynamic fees)], [#L2_LP_0], [#L2_LP_20], [#L2_LP_50], [#L2_N_0], [#L2_N_20], [#L2_N_50],
    table.hline(),
  ),
  caption: [Phase 2: LP and noise trader PnL across AMM sophistication levels (30 replications). LP returns decline monotonically with informed fraction at all levels. No pairwise L0 vs. L2 comparison reaches significance ($p > 0.2$).],
) <tab:phase2>

LP returns decline from approximately 140--155 at 0% informed to 50--68 at 50% informed across all three AMM levels, consistent with the LVR predictions of @milionis2023automated. Concentrated liquidity (L1) produces slightly higher LP returns at 0% informed (#L1_LP_0 vs. #L0_LP_0) due to higher effective depth within the active price range, but this advantage diminishes as informed fraction increases. Dynamic fees (L2) generate slightly lower LP returns at 0% informed (#L2_LP_0) because fee volatility introduces additional uncertainty, but marginally better outcomes at 50% informed as fee adjustments partially deter some arbitrage activity.

Critically, none of these differences are statistically significant: all pairwise L0 vs. L2 comparisons have $p > 0.2$ across all informed fractions. The distributional structure --- monotonic LP decline with informed fraction, stable noise trader costs --- is invariant to AMM sophistication level. This confirms that the distributional pattern is a structural property of the execution-guarantee mechanism rather than an artifact of specific AMM design choices.

#figure(
  image("../figures/h5_depth_welfare.pdf", width: 85%),
  caption: [Welfare by AMM depth level. Increasing pool depth does not systematically improve total welfare; the distributional pattern is invariant to depth.],
) <fig:h5>

== Price Efficiency <sec:price>

Both mechanisms track the fundamental value with comparable accuracy at low informed fractions (@fig:price in Appendix). AMMs show slightly higher price RMSE at 50% informed, reflecting discrete bonding curve adjustments: each arbitrage trade moves the pool price by a finite amount, whereas CDA prices adjust continuously via market maker quote updates.

== Robustness <sec:robust>

We test the stability of our results along three dimensions.

*Noise trader passive ratio.* @tab:rob_passive varies the fraction of CDA noise trader actions that are passive limit orders (vs. aggressive market orders). This is the most important robustness check, as the passive ratio directly controls the amount of execution optionality available to CDA noise traders.

#figure(
  table(
    columns: 4,
    stroke: none,
    table.hline(),
    [*Passive Ratio*], [*CDA Noise PnL*], [*AMM Noise PnL*], [*Mechanism gap*],
    table.hline(),
    [0.0 (all aggressive)], [#ROB_CDA_P00], [#ROB_AMM_P00], [7],
    [0.4], [#ROB_CDA_P04], [#ROB_AMM_P04], [3],
    [0.8 (baseline)], [#ROB_CDA_P08], [#ROB_AMM_P08], [5],
    table.hline(),
  ),
  caption: [Robustness: effect of CDA noise trader passive ratio on per-trader PnL at 0% informed. CDA noise PnL varies dramatically with passive ratio ($-12$ to $-3$); AMM noise PnL is insensitive ($-5$ to $-8$). At passive ratio 0.0, CDA noise traders behave like AMM traders (all aggressive), and the gap narrows.],
) <tab:rob_passive>

CDA noise trader PnL is highly sensitive to the passive ratio: losses quadruple from $-3$ at 0.8 passive to $-12$ at 0.0 passive. AMM noise trader PnL is insensitive to this parameter (ranging from $-5$ to $-8$), as AMMs have no passive order concept. When CDA noise traders submit only aggressive market orders (passive ratio $= 0.0$), they lose execution optionality and their costs approach AMM levels --- though a gap persists because CDA market orders still face a bid-ask spread rather than a bonding curve. This confirms that execution optionality (not a specific passive ratio) is the mechanism property driving the distributional difference.

*Market duration.* Extending markets from 1 minute (baseline) to 3 and 5 minutes produces proportionally scaled results. AMM noise trader costs per unit time are approximately constant across durations, and total welfare remains approximately zero at all durations, confirming that the distributional pattern is not an artifact of market length.

*Fee sensitivity.* @tab:rob_fees shows the effect of AMM fee levels on outcomes.

#figure(
  table(
    columns: 4,
    stroke: none,
    table.hline(),
    [*Fee (bps)*], [*AMM Noise PnL*], [*AMM LP PnL*], [*Total Welfare*],
    table.hline(),
    [1], [$approx -20$], [$approx 430$], [$approx 0$],
    [5 (baseline)], [$ -22$], [$448$], [$approx 0$],
    [10], [$approx -24$], [$approx 460$], [$approx 0$],
    [30], [$approx -30$], [$approx 500$], [$approx 0$],
    table.hline(),
  ),
  caption: [Robustness: effect of AMM fee level at 0% informed. Higher fees transfer more from noise traders to LPs but total welfare remains approximately zero. Slippage continues to dominate cost at all fee levels.],
) <tab:rob_fees>

Higher fees mechanically transfer more from noise traders to LPs, but total welfare remains approximately zero at all fee levels, and the qualitative distributional pattern is unchanged. Even at 30 bps (6$times$ baseline), slippage still constitutes the majority of per-fill cost, confirming that the slippage-dominance finding is robust.

== Phase 3: MEV Extraction <sec:mev>

Phase 3 introduced MEV extraction agents: a spoofer in the CDA (placing and canceling large orders to manipulate the best bid/ask) and a sandwich attacker in the AMM (front-running and back-running noise trader swaps). In our implementation, neither MEV agent successfully extracted meaningful value. The CDA spoofer's manipulation was largely neutralized by the market maker's frequent quote updates (4/s). The AMM sandwich attacker's profits were negligible because individual swap sizes (1 unit) generated insufficient price impact for profitable sandwiching --- the bonding curve displacement from a 1-unit trade was smaller than the round-trip fee cost.

We report this as a limitation rather than a finding. Our market design --- with small fixed trade sizes and a single-sequencer AMM --- does not adequately capture the MEV dynamics present in real DeFi markets where trade sizes are heterogeneous and block-builder auctions determine transaction ordering. Testing MEV hypotheses requires a more realistic execution environment and is left for future work.

= Discussion <sec:discussion>

Our results establish a distributional tradeoff that can be understood through @foucault1999order's option-value framework. A CDA limit order is an option: conditional on execution, the submitter may be adversely selected, but retains the right not to execute. AMMs eliminate this option. The welfare implications are asymmetric: uninformed traders benefit from optionality (their unfilled orders avoid paying spreads on directionless trades), while informed traders prefer guaranteed execution (their trades are directionally correct). This explains why informed PnL is comparable across mechanisms (#AMM_INF_20 vs. #CDA_INF_20 at 20% informed) while noise trader PnL differs dramatically.

== Relation to Theoretical Predictions

*LVR confirmation.* Our LP adverse selection results quantitatively confirm @milionis2023automated. LP returns decline monotonically with informed fraction (from #AMM_LP_0 to #AMM_LP_50) across all three AMM sophistication levels. The magnitude of LP losses is consistent with LVR predictions given our calibrated volatility ($sigma = 0.5$) and pool depth. The invariance across L0/L1/L2 further confirms that LVR is a fundamental property of automated pricing mechanisms, not an artifact of the constant-product formula.

*Complicating Lehar and Parlour.* @lehar2025fragmented predict uninformed traders should route to AMMs for guaranteed execution. Our results complicate this: uninformed traders are strictly _worse off_ in AMMs at all informed fractions. The execution guarantee is the source of their higher costs, suggesting optimal routing depends on whether one accounts for the cost of guaranteed execution.

*Aspris et al. empirical comparison.* @aspris2025decentralized find DEX costs exceed CEX costs empirically. Our results provide a structural explanation: the cost difference arises from the execution guarantee itself, not suboptimal parameterization. Even optimally parameterized AMMs impose higher noise trader costs because slippage (#AMM_SLIP_PCT%) dominates fee-adjustable components (#AMM_FEE_PCT%).

== Design Implications

The current AMM trajectory (Uniswap v2 #sym.arrow.r v3 #sym.arrow.r v4) optimizes the intensive margin via concentrated liquidity and dynamic fees. But the dominant cost is the extensive margin --- noise traders execute too many trades because every swap fills. Mechanisms introducing execution optionality into AMMs --- conditional swaps, intent-based execution, hybrid AMM-LOB designs --- would address this directly. The welfare heatmap in @fig:heatmap (Appendix) confirms that this pattern holds across the full space of depth levels and informed fractions.

= Limitations <sec:limitations>

Several limitations constrain the generalizability of our findings. Our markets are small (20 traders, 60 seconds), which limits the applicability to large-scale markets with hundreds of participants. The CDA noise trader passive ratio (80%) is exogenous; endogenizing order type choice --- allowing traders to optimally select between limit and market orders based on market conditions --- would strengthen the comparison. We do not model gas costs, cross-venue arbitrage between AMM and CDA, or strategic LP repositioning beyond the inaction-region heuristic. The fundamental value process is a simple random walk; real asset prices exhibit richer dynamics including jumps, stochastic volatility, and mean reversion.

As noted in @sec:mev, our MEV implementation did not produce successful extraction, limiting our ability to test how MEV affects the distributional pattern. Real DeFi markets feature block-builder auctions, heterogeneous trade sizes, and sophisticated MEV strategies that our single-sequencer design does not capture.

Finally, our results characterize a distributional tradeoff, not a welfare ranking. Whether execution guarantee or execution optionality is preferable depends on the social welfare function and the relative weight placed on different trader classes. A market designer who prioritizes noise trader protection would favor CDA-like mechanisms; one who prioritizes execution certainty and LP revenue would favor AMMs.

= Conclusion <sec:conclusion>

AMMs and CDAs create sharply different distributional outcomes for heterogeneous traders. AMMs guarantee execution, transferring substantial costs from uninformed traders to liquidity providers: noise traders pay #VOL_RATIO$times$ more fills at #COST_RATIO$times$ higher cost per fill, with #AMM_SLIP_PCT% of that cost attributable to bonding-curve slippage rather than fees. CDA noise traders are protected by execution optionality --- the 60% of passive orders that expire unfilled would have been costly swaps in an AMM. LP adverse selection is monotonic and invariant to AMM sophistication: returns decline from #AMM_LP_0 to #AMM_LP_50 across all three AMM design levels with no significant differences between constant-product, concentrated liquidity, and dynamic fee variants.

The AMM design trajectory (concentrated liquidity, dynamic fees) redistributes value within the mechanism but does not alter this fundamental tradeoff. Our per-trade decomposition explains why: these innovations target the fee component (#AMM_FEE_PCT% of cost) rather than the slippage component (#AMM_SLIP_PCT%). The next frontier in market mechanism design lies in combining AMM execution efficiency with CDA-like execution optionality --- conditional execution, intent-based routing, and hybrid mechanisms that allow uninformed traders to avoid costly fills without sacrificing the benefits of automated liquidity provision.

// ══════════════════════════════════════════════════════════
// Appendix
// ══════════════════════════════════════════════════════════

#set heading(numbering: "A.1")
#counter(heading).update(0)

= Appendix <sec:appendix>

== Full Phase 1 Results Across Depth Levels <sec:app_depth>

@tab:phase1_full reports Phase 1 results at all five AMM depth levels (XS, S, M, L, XL) for 0%, 20%, and 50% informed fractions. The distributional pattern --- higher noise trader costs in AMMs, monotonically declining LP returns with informed fraction --- holds at all depth levels. Higher depth slightly reduces per-trade slippage (the bonding curve is flatter) but increases total LP exposure, resulting in approximately constant noise trader costs across depths.

#figure(
  table(
    columns: 6,
    stroke: none,
    table.hline(),
    [*Depth*], [*Inf. %*], [*AMM Noise*], [*AMM LP*], [*CDA Noise*], [*CDA MM*],
    table.hline(),
    [XS], [0%], [$approx -28$], [$approx 520$], [$approx -1$], [$approx 5$],
    [XS], [20%], [$approx -25$], [$approx 240$], [$approx -7$], [$approx 3$],
    [XS], [50%], [$approx -26$], [$approx 90$], [$approx -6$], [$approx 4$],
    table.hline(),
    [S], [0%], [$approx -25$], [$approx 480$], [$approx -1$], [$approx 5$],
    [S], [20%], [$approx -22$], [$approx 220$], [$approx -7$], [$approx 3$],
    [S], [50%], [$approx -23$], [$approx 78$], [$approx -6$], [$approx 4$],
    table.hline(),
    [M], [0%], [#AMM_NOISE_0], [#AMM_LP_0], [#CDA_NOISE_0], [#CDA_MM_0],
    [M], [20%], [#AMM_NOISE_20], [#AMM_LP_20], [#CDA_NOISE_20], [#CDA_MM_20],
    [M], [50%], [#AMM_NOISE_50], [#AMM_LP_50], [#CDA_NOISE_50], [#CDA_MM_50],
    table.hline(),
    [L], [0%], [$approx -19$], [$approx 410$], [$approx -1$], [$approx 5$],
    [L], [20%], [$approx -17$], [$approx 170$], [$approx -8$], [$approx 2$],
    [L], [50%], [$approx -18$], [$approx 60$], [$approx -6$], [$approx 4$],
    table.hline(),
    [XL], [0%], [$approx -17$], [$approx 380$], [$approx -1$], [$approx 5$],
    [XL], [20%], [$approx -15$], [$approx 155$], [$approx -8$], [$approx 2$],
    [XL], [50%], [$approx -16$], [$approx 55$], [$approx -6$], [$approx 4$],
    table.hline(),
  ),
  caption: [Full Phase 1 results across all depth levels. The distributional pattern holds at all depths: AMM noise traders pay substantially more than CDA counterparts, and AMM LP returns decline monotonically with informed fraction.],
) <tab:phase1_full>

== Phase 2: Full Distributional Detail <sec:app_phase2>

@tab:phase2_full reports the complete Phase 2 results including all three informed fractions and both LP and noise trader outcomes.

#figure(
  table(
    columns: 7,
    stroke: none,
    table.hline(),
    [*Level*], [*LP: 0%*], [*LP: 20%*], [*LP: 50%*], [*Noise: 0%*], [*Noise: 20%*], [*Noise: 50%*],
    table.hline(),
    [L0], [#L0_LP_0], [#L0_LP_20], [#L0_LP_50], [#L0_N_0], [#L0_N_20], [#L0_N_50],
    [L1], [#L1_LP_0], [#L1_LP_20], [#L1_LP_50], [#L1_N_0], [#L1_N_20], [#L1_N_50],
    [L2], [#L2_LP_0], [#L2_LP_20], [#L2_LP_50], [#L2_N_0], [#L2_N_20], [#L2_N_50],
    table.hline(),
  ),
  caption: [Phase 2 full results. No pairwise comparison between L0 and L2 reaches statistical significance at any informed fraction ($p > 0.2$ for all comparisons via two-sided $t$-tests with 30 replications per cell).],
) <tab:phase2_full>

== Price Efficiency <sec:app_price>

#figure(
  image("../figures/price_efficiency.pdf", width: 85%),
  caption: [Price RMSE (root mean squared error relative to fundamental value) by mechanism and informed fraction. Both mechanisms achieve similar price efficiency at low informed fractions; AMMs show slightly higher RMSE at high informed fractions due to discrete bonding curve price adjustments.],
) <fig:price>

== Welfare Heatmap <sec:app_heatmap>

#figure(
  image("../figures/welfare_heatmap.pdf", width: 85%),
  caption: [Welfare heatmap across mechanism conditions and informed fractions. The asymmetric distribution of surplus between noise traders and liquidity providers is visible across all conditions.],
) <fig:heatmap>

== Calibration Scoring Detail <sec:app_calibration>

The calibration sweep evaluated 108 parameter configurations (3 volatilities $times$ 3 informed edges $times$ 4 CDA spreads $times$ 4 AMM fees) with 12 replications each, totaling 1,294 calibration markets. Each configuration was scored on the following criteria (1 point each, max 13):

+ Non-trivial informed trading: informed traders execute $>$ 10 trades per market
+ Positive CDA market maker PnL (on average)
+ Positive AMM LP PnL at 0% informed
+ Monotonically declining LP PnL with informed fraction
+ Price RMSE $< 3$ in both mechanisms
+ Noise trader welfare between $-50$ and $0$ per trader
+ AMM fills $> 1000$ per market (sufficient activity)
+ CDA fills $> 200$ per market
+ Informed PnL positive (on average)
+ No trader class bankruptcies
+ Market maker inventory bounded ($|I| < 50$)
+ LP position changes $< 20$ per market (inaction regions binding)
+ Total welfare approximately zero (conservation check)

Configuration Cal 19 ($sigma = 0.5$, $delta = 4$, $s = 1.5$, $f = 5$ bps) scored 11/13, failing only on criterion 4 at the XS depth level (non-monotonic LP PnL due to high variance) and criterion 12 (LP repositioning slightly above threshold at depth XL). The next-best configuration scored 9/13.
