---
source_pdf: "chaudhry2025_adjoint_dae_error.pdf"
pages: 36
source_words: 13986
references_removed: true
references_start_page: 31
extraction_quality: "good"
converter: "PyMuPDF-1.28.2"
---

# Adjoint-based A Posteriori Error Analysis for Semi-explicit Index-1 and Hessenberg Index-2 Differential-Algebraic Equations

[Open source PDF](../reference_papers_origin/chaudhry2025_adjoint_dae_error.pdf)

<!-- source-page: 1 -->

## Abstract

In this work we develop adjoint-based analyses for a posteriori error estimation for the temporal discretization of differential-algebraic equations (DAEs) of special type: semi-explicit index-1 and Hessenberg index-2. Our technique quantifies the error in a Quantity of Interest (QoI), which is defined as a bounded linear functional of the solution of a DAE. We derive representations for errors of various types of QoIs (depending on the entire time interval, final time, algebraic variables, differential variables, etc.). We develop two analyses: one that defines the adjoint to the DAE system, and one that first converts the DAE to an ODE system and then applies classical a posteriori analysis techniques. A number of examples are presented, including nonlinear and non-autonomous DAEs, as well as spatially discretized partial differential-algebraic equations (PDAEs). Numerical results indicate a high degree of accuracy in the error estimation.

## 1 Introduction

Differential-algebraic equations (DAEs) are a broad class of mathematical models that arise in a wide range of scientific and engineering applications where constraints are intrinsic to the system under consideration. Such systems arise in optimization, model simplification, optimal control, uncertainty quantification, and in modeling numerous 1 arXiv:2507.03712v2 [math.NA] 15 Aug 2025

<!-- source-page: 2 -->

physical phenomena. Examples include electrical circuits, combustion, and ion flow [1– 6]. DAEs are a generalization of ordinary differential equations (ODEs). Unlike ODEs, DAEs combine both differential dynamics and algebraic constraints, which introduce unique challenges for their analysis and numerical simulation. In this article we focus on DAEs containing only ordinary derivatives, as opposed to partial derivatives. However, discretization of PDEs with constrains often leads to DAEs such as those we consider in this work [5]. Numerical techniques for solving DAEs must handle complexities like stiffness and nonlinearity inherent to ODEs, but also the additional difficulties introduced by the algebraic structure, index, hidden constraints and consistency of initial conditions. The index of a DAE, which represents the complexity of its constraint structure, plays an important role in determining the appropriate numerical method. There are a number of techniques for the numerical solution of DAEs (see section 2.2 and the references therein). Solving DAEs numerically invariably involves error in the computed solution. This error in the computed solution must be quantified if DAEs are to be used in a robust and reliable manner in science and engineering applications. In this article we develop techniques to accurately quantify the error in a numerically computed Quantity-of- Interest (QoI) for DAEs. Adjoint based a posteriori error estimation plays a key role in accurate estimation of the error in the computed value of a QoI [7–10]. Adjoint based methods and analyses are used in numerous other applications, e.g., sensitivity analysis [4, 11–13], optimization [14–16], optimal control [17, 18], large-scale DAE solver: SUNDIALS [19, 20], neural network [21–23], and uncertainty quantification [24]. Although a well-developed theoretical framework for adjoint based a posteriori error estimation is available for ODEs as well as certain classes of partial differential equations (PDEs) [7, 9, 25–46], no such analysis has been carried out for DAEs to the best of our knowledge. However, DAEs have been analyzed in other contexts of error estimation and adjoint analysis. For example, error estimation for collocation solutions to linear index-1 DAEs has been studied in [47, 48], while local error control has been investigated in [49]. Various a priori error analyses have been carried out in [50–57]. The adjoint system for index-1 DAEs has been analyzed in [58]. Adjoint based sensitivity analysis for DAEs has been carried out in [4]. In this article we carry out a thorough adjoint based error analysis for semi-explicit index-1 and Hessenberg index-2 DAEs. In particular, this involves defining the associated adjoint DAE with consistent initialization depending on the structure of the QoI, and using the adjoint solution to quantify the error in the computed QoI. The theoretical results in this article derive accurate error estimates for various QoIs ( e.g. depending on final time, average over time intervals, involving either differential or algebraic variables, or both). We develop two error analyses in this article. The first approach is based on defining the adjoint directly to the DAE system, and requires careful setting of the adjoint initial conditions. The second approach defines an adjoint problem to the ODE corresponding to the DAE, which in turn allows the use of classical error analyses techniques. The accuracy of the resulting error estimates is demonstrated through a number of numerical examples including nonlinear, non-autonomous DAEs as well as a semi-discretized PDE. 2

<!-- source-page: 3 -->

The remainder of this paper is organized as follows: In section 2 we discuss two special types of DAEs; semi-explicit index-1 and Hessenberg index-2 DAEs. Further we discuss their numerical treatment and also introduce quantities of interest in this section. In sections 3 and 4 we develop two distinct analyses to quantify the error in the QoI for DAEs of type semi-explicit index-1 and Hessenberg index-2. The first technique, called Adjoint DAE, is based on forming an adjoint to the DAE system and is presented in section 3. The second technique, called Adjoint ODE and discussed in section 4, first forms an ODE system corresponding to the DAE and then utilizes the adjoint to the ODE system. In section 5 we discuss implementation aspects and formation of error estimates. We show numerical results for several examples, including nonlinear, non-autonomous DAEs, and a system of partial differential-algebraic equations, in section 6. In section 7 we give a summary of our contributions with potential directions for future research.

## 2 Quantities of Interest in Differential Algebraic

Equations This sections gives a brief background on semi-explicit index-1 and Hessenberg index-2 Differential-Algebraic Equations (DAEs), their numerical approximation, and introduces two quantities of interest (QoIs) that are the focus of error estimation of this article.

### 2.1 Semi-explicit DAEs

Consider the semi-explicit DAE, ˙y = f(y, z, t), (1a) 0 = g(y, z, t), (1b) where y(t) ∈Rn and z(t) ∈Rm are called the differential and algebraic variables respectively. This form of a DAE, which is an ODE with constraints, arises in numerous science and engineering applications [5]. Clearly, the initial conditions y0 = y(0), z0 = z(0) must satisfy the condition that g(y0, z0, 0) = 0. (2) That is to say, that the initial conditions must satisfy the algebraic constraint in order to be “consistent.” The index of a DAE is an important property of the problem that plays a role in classification and has many consequences for the behavior of solutions [5]. There are, in fact, several distinct, but related, definitions of the index of a DAE. Here we restrict ourselves to the discussion of the “differential index.” For a DAE of the form given by eq. (1), the differential index is the minimum number of times the algebraic constraint equations needs to be differentiated in order to obtain differential equations for all of the algebraic variables [59]. Throughout this article we assume that the DAE eq. (1) is either index-1 or index-2. 3

<!-- source-page: 4 -->

#### 2.1.1 Semi-explicit index-1 DAE

Consider a semi-explicit DAE of the form eq. (1). Differentiating the algebraic constraint eq. (1b) with respect to t and formally solving for ˙z gives ˙z = −[gz]−1 [gyf + gt] , (3) where gy = ∂g/∂y ∈Rm×n is the Jacobian matrix of the function g with respect to y and the ij-th component of gy is: (gy)ij = ∂gi ∂yj for i = 1, 2, . . . , m, and j = 1, 2, . . . , n. Similarly, gz ∈Rm×m is the Jacobian of g with respect to z and gt = ∂g ∂t . It follows from eq. (3) that the invertibility of the Jacobian matrix gz in a neighborhood of the solution of eq. (1) is required to yield explicit differential equations corresponding to the algebraic variables z(t) [6]. Indeed, the DAE eq. (1) is index-1 if and only if gz is invertible [5].

#### 2.1.2 Hessenberg (Pure) index-2 DAE

We now consider a common class of DAEs for which the index is greater than one. Consider the semi-explicit DAE in case that the algebraic constraint eq. (1b) does not explicitly depend on the algebraic variable z. In this case, the DAE may be written, ˙y = f(y, z, t), (4a) 0 = g(y, t). (4b) Taking the derivative of eq. (4b) with respect to t yields the so-called hidden constraint, 0 = gyf + gt. (5) Now, in the event that gyfz ∈Rm×m is invertible, the ODE eq. (4a) together with the hidden constraint eq. (5) form a index-1 DAE [6]. To see this, we differentiate the hidden constraint eq. (5) with respect to time and formally solve for ˙z to yield the differential equations corresponding to the algebraic variables, ˙z = −(gyfz)−1  f T gyyf + gyfyf + 2gytf + gyft + gtt  , (6) here, gyy is the derivative of the Jacobian matrix gy with respect to y, a third order tensor of dimension m × n × n with components given by (gyy)ijk = ∂2gi ∂yj∂yk , for i = 1, 2, . . . , m, j = 1, 2, . . . , n, and k = 1, 2, . . . , n. 4

<!-- source-page: 5 -->

For a fixed i, each slice of this tensor represents a Hessian matrix. Because f ∈Rn, f T gyyf has components  f T gyyf  i = n X j=1 n X k=1 ∂2gi ∂yj∂yk fjfk, for i = 1, 2, . . . , m. The DAE eq. (4) with gyfz nonsingular in a neighborhood of the solution is called Hessenberg (Pure) index-2 DAE [5]. This is called a pure index-2 because all the algebraic variables (components of z) are of index-2. The initial conditions (y0 = y(0), z0 = z(0) must now satisfy 0 = g(y0, 0), and 0 = gy(y0, 0)f(y0, z0, 0) + gt(y0, 0), (7) in order to be consistent [6].

### 2.2 Numerical Solution of DAEs

There are two main ways to solve DAEs numerically. The first is to directly discretize the DAE as written. The second is to reformulate the DAE as an ODE through a process known as index reduction, and then numerically solve that ODE. Direct discretization is often preferred due to the cost of index reduction and to preserve the constraint eq. (1b) exactly for the numerical solution. The well studied class of numerical methods for ODEs called backward differentiation formula (BDF) methods were applied first in 1971 by Gear [60] to solve DAEs numerically. These methods serve as the basis for the DASSL code [5, 61]. It is known that the p-step BDF method is accurate to order p for p ≤6 and effective for solving index-1 as well as Hessenberg index-2 DAEs numerically [5, 59]. We denote the approximate solution to eq. (1) or eq. (4) as [Y (t), Z(t)]T , where Y (t) ∈Rn and Z(t) ∈Rm. In this work, we use the simplest first order BDF method, also known as the Implicit Euler Method, for the numerical solution of index-1 eq. (1) as well as Hessenberg index-2 DAEs eq. (4). This method is first order accurate, stable and convergent for semi-explicit index-1 and Hessenberg index-2 DAEs [59]. The approximate solution is calculated at a discrete set of nodes, 0 = t0 < t1 < t2 < · · · < tN = T. (8) We take these nodes to be evenly spaced, tk = t0 + k∆t, k = 0, 1, 2, . . . , N, where ∆t = T/N. Let Yk = Y (tk), and Zk = Z(tk) for k = 0, 1, . . . , N, and set Y0 = y(0), Z0 = z(0). Applying the BDF-1 method to the DAE eq. (1) yields, Yk+1 = Yk + ∆tf(Yk+1, Zk+1, tk+1), 0 = g(Yk+1, Zk+1, tk+1), ) (9) for k = 0, 1, . . . , N −1. In the case of Hessenberg (Pure) index-2 DAE eq. (4), the constraint equation does not explicitly depend on the algebraic variable and the first 5

<!-- source-page: 6 -->

order BDF method becomes Yk+1 = Yk + ∆tf(Yk+1, Zk+1, tk+1), 0 = g(Yk+1, tk+1), ) (10) for k = 0, 1, . . . , N −1. This discretization is implicit in time and yields a system of n + m equations in n + m unknowns. Given values for Yk, and Zk, one must solve this nonlinear system for Yk+1, and Zk+1. The numerically computed solution to the index-1 DAEs eq. (1) and index-2 DAEs eq. (4) are naturally calculated at the discrete time points tk. In this work, whenever we must evaluate the numerical solution any other time point t ∈(0, T], we do so using linear interpolation between the two closet time points such that t ∈(tk, tk+1).

### 2.3 Quantity of Interest (QoI)

In this section we formalize the notion of a Quantity of Interest or QoI. In many applications, the approximate solution of an DAE is used to calculate some measurable quantity, called the QoI. In this work we model QoIs as measurable quantities that can be expressed as a linear functional acting on the solution of the DAE. To describe the QoIs considered, we first introduce some notation. For any two time-dependent functions a, b ∈[L2(0, T]]d, we define ⟨a, b⟩= Z T 0 (a(t), b(t)) dt, (11) where (·, ·) is the usual Euclidean inner-product in Rd. We consider two types of QoI in this work. The first QoI is defined over the interval [0, T] as, Q[0,T ](y, z) = ⟨y, ψy⟩+ ⟨z, ψz⟩, (12) where ψy ∈[L2(0, T]]n and ψz ∈[L2(0, T]]m. The other type of QoI depends only on the solution at the terminal time T, and is defined as, QT (y, z) = (y(T), ζy) + (z(T), ζz) , (13) where ζy ∈Rn and ζz ∈Rm.

### 2.4 Error in QoI

Now, given an approximate solution to a DAE, our main goal is to calculate the error in the computed value of the QoIs. Recalling that [y, z]T is the true solution of eq. (1) and [Y, Z]T the numerically computed solution, let e(y) = (y −Y ) and e(z) = (z −Z). The errors in the two QoIs, based on the definition in eqs. (12) and (13), are given below. 6

<!-- source-page: 7 -->

• The error in the QoI Q[0,T ](Y, Z) is eQ[0,T ] := Q[0,T ](y, z) −Q[0,T ](Y, Z) = ⟨e(y), ψy⟩+ ⟨e(z), ψz⟩. (14) • Similarly, the error in the QoI QT (Y, Z) is eQT := QT (y, z) −QT (Y, Z) =  e(y)(T), ζy +  e(z)(T), ζz . (15) Quantifying these errors is the focus of the next two sections. In section 3, the analysis is carried out by defining an adjoint problem to the DAE system eq. (1). Later, in section 4, index reduction is used to convert the DAE to an ODE, and then classical analysis is employed to derive error estimates.

## 3 Error Analysis of DAEs by Adjoint to the DAE

system The error analysis in this section, called Adjoint DAE analysis, is carried out by defining an adjoint problem to the DAE system eq. (1), and by a careful choice of the initial conditions for the adjoint problem.

### 3.1 Adjoint System

We introduce adjoint differential variables ϕ(y)(t) ∈Rn and adjoint algebraic variables ϕ(z)(t) ∈Rm, and define the corresponding adjoint problem for a system of semiexplicit DAE eq. (1) as follows, −˙ϕ(y) = ¯f T y ϕ(y) + ¯gT y ϕ(z) + ψy, t ∈[0, T), (16a) 0 = ¯f T z ϕ(y) + ¯gT z ϕ(z) + ψz, t ∈[0, T), (16b) where the linearized operators are ¯fy = Z 1 0 ∂f(˜y, ˜z) ∂y ds ∈Rn×n, ¯fz = Z 1 0 ∂f(˜y, ˜z) ∂z ds ∈Rn×m, ¯gy = Z 1 0 ∂g(˜y, ˜z) ∂y ds ∈Rm×n, ¯gz = Z 1 0 ∂g(˜y, ˜z) ∂z ds ∈Rm×m, for ˜y = sy + (1 −s)Y , and ˜z = sz + (1 −s)Z. The consistent initial conditions corresponding to adjoint algebraic variables ϕ(z) at t = T are, ϕ(z)(T) =    −  ¯gT z −1  ¯f T z ϕ(y) + ψz

t=T , if adjoint DAE is index-1, −   ¯f T z ¯gT y −1  ¯f T z ¯f T y ϕ(y) + ¯f T z ψy −ψz t 

t=T , if adjoint DAE is index-2. (17) These conditions follow directly from eqs. (2) and (7). Here, we leave the initial conditions ϕ(y)(T) unspecified for the moment. 7

<!-- source-page: 8 -->

Theorem 3.1 The adjoint DAE system eq. (16) preserves the index structure of the the original DAE system eq. (1) provided the numerical solution [Y, Z]T is sufficiently close to the true solution [y, z]T . That is, the adjoint DAE system has the same index as the original DAE provided e(y) and e(z) are sufficiently small. Proof First assume the DAE eq. (1) is index-1. Then, from the discussion in section 2.1.1, the adjoint DAE eq. (16) is index-1 if and only if ¯gTz , or equivalently, ¯gz is invertible. Now, since the original DAE is index-1, gz is invertible. However, this does not directly imply that ¯gz is also invertible. Note that ¯gz may be written as, ¯gz = Z 1 0 gz(se(y) + Y, se(z) + Z)ds. Consider the following function of [u, v]T ∈Rn+m, G(u, v) = det "Z 1 0 gz(su + Y, sv + Z)ds # , where det denotes the determinant. Now G(u, v) is a continuous function of u and v since the determinant is a continuous function of its entries. Further, G(0, 0) = det[gz(Y, Z)]̸ = 0 since gz is invertible. Without loss of generality assume that G(0, 0) > 0. Then from the continuity of G, there is a ball of radius ϵ around [0, 0]T , Bϵ([0, 0]T ), such that G(u, v) > 0 for [u, v]T ∈Bϵ([0, 0]T ). Noting that G(e(y, e(z)) = det[¯gz], we conclude that ¯gz is invertible for e(y) and e(z) sufficiently small. A similar argument shows that the adjoint DAE is index-2 if the original DAE is index-2 and e(y) and e(z) are sufficiently small. □ Defining the correct initial conditions for ϕ(y)(T) is a key component of analysis, and is motivated from the work on adjoint based sensitivity analysis in [4]. For the adjoint DAE eq. (16), the initial conditions must be set in a manner determined by the index of the original DAE as well as the dependency of QoIs over the interval [0, T], and at the terminal time T, as we show in later sections. For now, we note some properties of the linearized operators used later in the analysis. By the fundamental theorem of calculus, f(y, z) −f(Y, Z) = Z 1 0 d ds [f(sy + (1 −s)Y, sz + (1 −s)Z)] ds, = Z 1 0 ∂f ∂y ds (y −Y ) + Z 1 0 ∂f ∂z ds (z −Z), = ¯fy(y −Y ) + ¯fz(z −Z), so, we have ¯fy(y −Y ) + ¯fz(z −Z) = f(y, z) −f(Y, Z), (18) similarly, ¯gy(y −Y ) + ¯gz(z −Z) = g(y, z) −g(Y, Z). (19) 8

<!-- source-page: 9 -->

The following lemma is used in deriving error representations later. Lemma 3.1 We have eQ[0,T ] =  ϕ(y)(0), e(y)(0)  −  ϕ(y)(T), y(T) −Y (T)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y, Z)⟩. (20) The proof is quite similar to standard proofs for error analysis of ODEs, however, for completeness we include it in appendix A.

### 3.2 Error Analysis for Semi-explicit Index-1 DAE

Now we derive error representations for QoIs computed from the numerical solution of index-1 DAEs. The error in semi-explicit index 1 DAE for the computed QoI Q[0,T ](Y, Z) is analyzed in theorem 3.2, while the error in the computed QoI QT (Y, Z) is analyzed in theorem 3.3. Theorem 3.2 Let ϕ(y)(T) = 0 in the adjoint problem eq. (16). Then the error in the computed QoI Q[0,T ](Y, Z) is, eQ[0,T ] =  ϕ(y)(0), e(y)(0)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y, Z)⟩. (21) Proof The proof directly follows from the lemma 3.1 by setting ϕ(y)(T) = 0. □ Theorem 3.3 Let ψy(t) = 0, and ψz(t) = 0 in eq. (16), and the adjoint initial condition given by ϕ(y)(T) = ζy −¯gT y  ¯gT z −1

t=T ζz. (22) Then the error in the computed QoI QT (Y, Z), is given by eQT =  ϕ(y)(0), e(y)(0)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y, Z)⟩. (23) Proof Substituting ψy(t) = 0, and ψz(t) = 0 in lemma 3.1, we have  ϕ(y)(T), y(T) −Y (T)  = ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y, Z)⟩+  ϕ(y)(0), y(0) −Y (0)  . (24) Considering the left hand side of eq. (24) and using eq. (22) and eq. (19),  ϕ(y)(T), e(y)(T)  =  ζy, e(y)(T)  −  ¯gT y  ¯gT z −1 ζz, y −Y 

t=T , =  ζy, e(y)(T)  −  ¯gT z −1 ζz, ¯gy (y −Y ) 

t=T , 9

<!-- source-page: 10 -->

=  ζy, e(y)(T)  −  ¯gT z −1 ζz, g(y, z) −g(Y, Z) −¯gz(z −Z) 

t=T , =  ζy, e(y)(T)  +  ¯gT z −1 ζz, g(Y, Z) 

t=T +  ¯gT z −1 ζz, ¯gz(z −Z) 

t=T , =  ζy, e(y)(T)  +  ζz, e(z)(T)  , where we used g(Y, Z)|t=T =tN = 0 in the last step. Combining this with eq. (24) and noticing that eQT =  ζy, e(y)(T)  +  ζz, e(z)(T)  proves the theorem. □ Remark 3.1 Quite often the QoI QT (y, z) depends on only y, i.e., QT (y, z) = (y(T), ζy). In this case we have ζz = 0, and the initial condition simplifies to ϕ(y)(T) = ζy, while the error representation remains (23).

### 3.3 Error Analysis for Hessenberg Index-2 DAE

The error in Hessenberg index 2 DAE for the computed QoI Q[0,T ](Y, Z) is analyzed in theorem 3.4, while the error in the computed QoI QT (Y, Z) is analyzed in theorem 3.5. Theorem 3.4 Consider eq. (16) and let ϕ(y)(T) be given by ϕ(y)(T) = −¯gT y  ¯fT z ¯gT y −1 ψz

t=T . (25) Then the error in the computed QoI Q[0,T ](Y, Z), is given by eQ[0,T ] =  ϕ(y)(0), e(y)(0)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y )⟩. (26) Proof Since g is independent of z, we have ¯gz = 0. Using this in lemma 3.1 leads to, eQ[0,T ] =  ϕ(y)(0), e(y)(0)  −  ϕ(y)(T), y(T) −Y (T)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y )⟩. (27) Clearly, the term  ϕ(y)(T), y(T) −Y (T)  in eq. (27) is not computable because of the presence of unknown y(T). Using eq. (25) in this term, followed by eq. (19) leads to,  ϕ(y)(T), y(T) −Y (T)  =  −¯gT y  ¯fT z ¯gT y −1 ψz, e(y) 

t=T , = −  ¯fT z ¯gT y −1 ψz, ¯gy(y −Y ) 

t=T , = −  ¯fT z ¯gT y −1 ψz, g(y) −g(Y ) 

t=T , = 0, (28) where we used g(y) = 0, and g(Y )|t=T =tN = 0 in the last step. Combining eq. (28) and eq. (27) proves the result. □ 10

<!-- source-page: 11 -->

Next we prove some technical results which are utilized in the analysis for the computed QoI QT (Y, Z). To this end we define, P = I −¯fz  ¯gy ¯fz −1 ¯gy. (29) Lemma 3.2 We have, 1.  P T ζy, e(y) =  ( ¯f T z ¯gT y )−1 ¯f T z ζy, g(Y )  , 2.  −P T ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, e(y) = −  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(y, z)  +  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(Y, Z)  +  ζz, e(z) −  ( ¯f T z ¯gT y )−1 ¯f T z ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, g(Y )  , 3.

d¯gT y dt   ¯f T z ¯gT y −1 ζz, e(y) ! = −   ¯f T z ¯gT y −1 ζz, dg(Y ) dt  −  ¯gT y   ¯f T z ¯gT y −1 ζz, f(y, z)  +  ¯gT y   ¯f T z ¯gT y −1 ζz, ˙Y  , where all the functions are evaluated at a fixed but arbitrary t ∈[0, T]. The proof of the lemma is given in appendix A. Theorem 3.5 Consider eq. (16) with ψy(t) = 0, ψz(t) = 0, and the initial condition for ϕ(y)(T) given by ϕ(y)(T) = P T " ζy −¯fT y ¯gT y ( ¯fT z ¯gT y )−1ζz −d¯gTy dt  ¯fT z ¯gT y −1 ζz # t=T (30) Then the error in the computed QoI QT (Y, X), is given by eQT =  ϕ(y)(0), e(y)(0)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y )⟩ −  ¯gT y ( ¯fT z ¯gT y )−1ζz, f(Y, Z) −˙Y 

t=T −  ¯fT z ¯gT y −1 ζz, dg(Y ) dt 

t=T . (31) Proof Starting from equation eq. (24) we have  ϕ(y)(T), y(T) −Y (T)  =  ϕ(y)(0), e(y)(0)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y )⟩. (32) Focusing on the left hand side of eq. (32) by combining it with eq. (30) we arrive at,  ϕ(y)(T), e(y)(T)  =

P T " ζy −¯fT y ¯gT y ( ¯fT z ¯gT y )−1ζz −d¯gTy dt  ¯fT z ¯gT y −1 ζz # , e(y) !

t=T , =  P T ζy, e(y)(T) 

t=T +  −P T ¯fT y ¯gT y ( ¯fT z ¯gT y )−1ζz, e(y)(T) 

t=T 11

<!-- source-page: 12 -->

−

d¯gTy dt  ¯fT z ¯gT y −1 ζz, e(y)(T) !

t=T (33) Applying lemma 3.2 to the terms in eq. (33),  ϕ(y)(T), e(y)(T)  =  ζy, e(y)(T)  +  ( ¯fT z ¯gT y )−1 ¯fT z ζy, g(Y ) 

t=T −  ¯gT y ( ¯fT z ¯gT y )−1ζz, f(y, z) 

t=T +  ¯gT y ( ¯fT z ¯gT y )−1ζz, f(Y, Z) 

t=T +  ζz, e(z)(T)  −  ( ¯fT z ¯gT y )−1 ¯fT z ¯fT y ¯gT y ( ¯fT z ¯gT y )−1ζz, g(Y ) 

t=T +  ¯fT z ¯gT y −1 ζz, dg(Y ) dt 

t=T +  ¯gT y  ¯fT z ¯gT y −1 ζz, f(y, z) 

t=T −  ¯gT y  ¯fT z ¯gT y −1 ζz, ˙Y 

t=T , = eQT +  ¯gT y ( ¯fT z ¯gT y )−1ζz, f(Y, Z) −˙Y 

t=T +  ¯fT z ¯gT y −1 ζz, dg(Y ) dt 

t=T , (34) where we used g(Y )|t=T =tN = 0 in the last step. Combining this equation with eq. (32) proves the result. □ Remark 3.2 Quite often the QoI QT (y, z) at t = T depends on only y, i.e., QT (y, z) = (y(T), ζy). In this case we have ζz = 0, and the initial condition simplifies to ϕ(y)(T) =  I −¯gT y ( ¯fT z ¯gT y )−1 ¯fT z  ζy

t=T , (35) while the error representation (31) takes the form, eQT =  e(y)(0), ϕ(y)(0)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y )⟩. (36)

## 4 Error Analysis of DAEs by Adjoint to the

Index-Reduced ODE system A DAE corresponds to an ODE (index-0 DAE) with an invariant [62]. We take advantage of this fact to utilize classical error analysis techniques to form error estimates for DAEs. Note that the corresponding ODE system is never solved numerically, and is only an analytical device used to derive error representations. We refer to the resulting error analysis as the Adjoint ODE analysis.

### 4.1 Adjoint System

For the DAE eq. (1) the corresponding ODE is ˙y = f(y, z, t), (37a) ˙z = h(y, z, t). (37b) with an invariant g(y, z, t) = 0, and an additional invariant eq. (5) for index-2 DAE. The function h(y, z, t) is defined by eq. (3) if the DAE is index-1 and by eq. (6) if the 12

<!-- source-page: 13 -->

DAE is index-2, h = ( −[gz]−1 [gyf + gt] , if DAE is index-1, −(gyfz)−1  f T gyyf + gyfyf + 2gytf + gyft + gtt  , if DAE is index-2. (38) Note that eqs. (1) and (37) have the same solution the solution [y, z]T . We define the corresponding adjoint ODE system for eq. (37) as follows: −˙ν(y) = ¯f T y ν(y) + ¯hT y ν(z) + ψy, t ∈[0, T), (39a) −˙ν(z) = ¯f T z ν(y) + ¯hT z ν(z) + ψz, t ∈[0, T), (39b) with the initial condition ν(y)(T), and ν(z)(T) unspecified, for the moment. Here ¯hy = Z 1 0 ∂h(˜y, ˜z) ∂y ds ∈Rm×n, ¯hz = Z 1 0 ∂h(˜y, ˜z) ∂z ds ∈Rm×m, for ˜y = sy + (1 −s)Y , and ˜z = sz + (1 −s)Z. Similar to eq. (18) and eq. (19) we have, ¯hy(y −Y ) + ¯hz(z −Z) = h(y, z) −h(Y, Z). (40)

### 4.2 Error Analysis for Semi-explicit Index-1 and Hessenberg

Index-2 DAE Lemma 4.1 We have, eQ[0,T ] + eQT =  ν(y)(0), e(y)(0)  +  ν(z)(0), e(z)(0)  + ⟨ν(y), f(Y, Z) −˙Y ⟩+ ⟨ν(z), h(Y, Z) −˙Z⟩. (41) Proof The proof is standard see [7]. □ The Adjoint ODE approach is conceptually simpler than the Adjoint DAE approach in the sense that only a single analysis is required for both Index-1 and Index-2 DAEs. However, we do need slightly different analyses for the two QoIs. These results are given in theorem 4.1 and theorem 4.2 below. Theorem 4.1 Let ν(y)(T) = 0, and ν(z)(T) = 0 in the adjoint problem eq. (39). Then the error in the computed QoI Q[0,T ](Y, Z) is, eQ[0,T ] =  ν(y)(0), e(y)(0)  +  ν(z)(0), e(z)(0)  + ⟨ν(y), f(Y, Z) −˙Y ⟩+ ⟨ν(z), h(Y, Z) −˙Z⟩. (42) Proof The proof directly follows from lemma 4.1 by setting the initial condition ν(y)(T) = 0, and ν(z)(T) = 0. □ 13

<!-- source-page: 14 -->

Theorem 4.2 Let ψy(t) = 0, ψz(t) = 0 in eq. (39), and the initial condition is given by ν(y)(T) = ζy, ν(z)(T) = ζz. Then the error in the computed QoI QT (Y, Z), is given by eQT =  ν(y)(0), e(y)(0)  +  ν(z)(0), e(z)(0)  + ⟨ν(y), f(Y, Z) −˙Y ⟩+ ⟨ν(z), h(Y, Z) −˙Z⟩. (43) Proof The proof follows directly from lemma 4.1 by substituting ψy(t) = 0, and ψz(t) = 0. □

## 5 Error Estimates

The error representations in theorems 3.2 to 3.5 (based on Adjoint DAE) and theorems 4.1 and 4.2 (based on Adjoint ODE) are exact, however, they involve the unknown true adjoint solution. Once we replace this adjoint solution by its numerical approximation (as discussed below in section 5.1), we obtain an error estimate from the corresponding error representation. More precisely, the error estimates based on Adjoint DAE are the right-hand sides of eqs. (21), (23), (26), (31) and (36) with ϕ(y) and ϕ(z) replaced by their numerical approximations ϕ (y) and ϕ (z). Similarly, error estimates based on the Adjoint ODE are the right-hand sides of eqs. (42) and (43). Since the error estimate is exactly the same as the error representation, except with the adjoint solution replaced by its numerical approximation, we avoid re-writing the error estimates separately. However, now our error estimates no longer capture the exact error, so their accuracy must be quantified. This aspect is discussed in section 5.3. Finally, in section 5.4 we discuss the relative advantages and disadvantages of the error estimates formed from the Adjoint DAE and Adjoint ODE analyses.

### 5.1 Numerical Solution of Adjoint DAE and Adjoint ODE

We now describe the numerical approximation to the adjoint solution in either the DAE eq. (16) or ODE eq. (39). The adjoint equations eqs. (16) and (39) technically require the true solution in the linearized operators ¯fy, ¯gy, ¯gz and ¯hy. However, in forming the numerical approximation of the adjoint problem, we substitute the approximate solution [Y, Z]T for the true solution [y, z]T in the linearized operators as is standard in adjoint based error estimation [33, 36, 39, 44]. That is, we approximate ¯fy, ¯fz, ¯gy, ¯gz, ¯hy, and ¯hz (see sections 3.1 and 4.1 for the definitions of these operators) as follows ¯fy ≈∂f ∂y

y=Y,z=Z, ¯fz ≈∂f ∂z

y=Y,z=Z, ¯gy ≈∂g ∂y

y=Y,z=Z, ¯gz ≈∂g ∂z

y=Y,z=Z, , ¯hy ≈∂h ∂y

y=Y,z=Z, ¯hz ≈∂h ∂z

y=Y,z=Z. Next, we discretize the DAE eq. (16) or the ODE eq. (39) using the BDF-1 (Implicit Euler) method. As we wish to assess the error in the temporal discretization of the original DAE, we adopt strategies to reduce the error associated with the adjoint problem. In particular, we numerically solve the adjoint problem on a more refined 14

<!-- source-page: 15 -->

temporal grid. We define the adjoint time grid points ˜tj = t0+j∆˜t for j = 0, 1, 2, . . . , ˜N with step size ∆˜t = ∆t/r. This means that the adjoint problem is solved with a step size that is r times smaller than step size used to solve the original DAE problem. For the experiments presented below, we use r = 4 except for example 6.5 where we use r = 3 (simply to reduce computational time). Although the adjoint problem is solved on a finer grid, the adjoint problem (eq. (16) or eq. (39)) is linear, and hence does not require a nonlinear solve, which might be required for the numerical solution of the original DAE (eq. (1) or eq. (4)). Whenever we require the evaluation of a Jacobian matrix in order to approximate ¯fy, ¯fz, ¯gy, ¯gz, ¯hy, or ¯hz at the adjoint time grid points ˜tj, we use linear interpolation of Y and Z from the original time grid, as discussed in section 2.2. Both the adjoint problems eqs. (16) and (39) are solved backwards in time from T to 0, using the first order BDF method discussed in section 2.2. Initial conditions (given at time t = T, which is the terminal time for the original DAE eq. (1)) are chosen according to the error representation we wish to assess. This produces the approximate solutions [ϕ (y), ϕ (z)]T (≈[ϕ(y), ϕ(z)]T ) and [ν(y), ν(z)]T (≈[ν(y), ν(z)]T ), respectively.

### 5.2 Evaluation of the Integrals

Error estimates in theorems 3.2 to 3.5, 4.1 and 4.2 involve integrals of the form ⟨a, b⟩= Z T 0 (a(t), b(t)) dt = N−1 X k=0 Z tk+1 tk (a(t), b(t)) dt. We approximate the integral Z tk+1 tk (a(t), b(t)) dt by a 5-point Gauss-Legendre quadrature on [tk, tk+1].

### 5.3 Effectivity Ratio

To quantify the accuracy of the error estimates (formed by evaluating the right-hand side of theorems 3.2 to 3.5, 4.1 and 4.2, and replacing the adjoint solution by its numerical approximation) we utilize a quantity called the “effectivity ratio.” The effectivity ratio is defined as Effectivity Ratio = Error Estimate Reference Error. Ideally, the reference error would simply be the difference between the true QoI and the QoI computed using the approximate solution to the DAE (i.e. eQ[0,T ] or eQT depending on context). This quantity corresponds to the left hand side of our error representations (theorems 3.2 to 3.5, 4.1 and 4.2). However, as we do not always have access to the true solution [y, z]T , we typically utilize a numerical solution obtained via standard software packages using very tight tolerances. In the following numerical tests, we reduce the original DAE to an ODE via index reduction (eq. (37)), and then 15

<!-- source-page: 16 -->

solve this ODE numerically using SciPy’s solve ivp routine [63]. We utilize absolute tolerance atol = 1e−15 and relative tolerance rtol = 1e−12 to obtain a highly accurate approximation of the true solution, and use this to define the reference error. However, in example 6.5, we have access to the analytical solution, and therefore avoid this extra layer of approximation.

### 5.4 Comparison of the Adjoint DAE and Adjoint ODE Error

Estimates The Adjoint ODE analysis (theorems 4.1 and 4.2) involves unified results for index-1 and index-2 DAEs, and hence is conceptually simpler than the Adjoint DAE analysis (theorems 3.2 to 3.5) which has distinct analyses depending on the index of the DAE. However, the error estimates formed using Adjoint ODE analysis incur a higher computational cost than the corresponding ones for Adjoint DAE analysis. The Adjoint ODE analysis involves evaluating the function h and its Jacobians ¯hy and ¯hz, while the corresponding terms in the Adjoint DAE analysis are evaluations of the functions g and its Jacobians ¯gy and ¯gz. The function h (see eq. (38)) and its Jacobians may be significantly more expensive to evaluate relative to the function g and its Jacobians. Moreover, as eq. (38) makes clear, evaluating the function h is more expensive for an index-2 DAE than it is for an index-1 DAE. Thus, while the Adjoint ODE analysis may be conceptually simpler, in practice it may be computationally prohibitive, especially for index-2 DAEs with a large dimension (see example 6.5).

## 6 Numerical Results

We present here a series of numerical tests whereby we evaluate the performance of error estimates for both semi-explicit index-1 and Hessenberg index-2 DAEs. We explore the cases of linear, nonlinear, autonomous, and non autonomous DAEs. We also test our error estimate on a system derived from a finite difference discretization of the Electro-Neutral Nernst-Planck Equations (ENNPE), which form a system of nonlinear Partial Differential Algebraic Equations (PDAEs). In all cases, we solve the DAE in question (eq. (1) or eq. (4)) using the first order BDF method as described in section 2.2. In our implementation, we use the Python routine scipy.optimize (fsolve) [63] to solve the implicit systems given by eq. (9) and eq. (10). Initial conditions are chosen to ensure consistency (i.e. to satisfy the explicit constraint equation and the hidden constraint, if any). In sections 6.1 and 6.2 we present results for index-1 and Hessenberg index-2 DAEs. A DAE arising from a PDE with constraints is investigated in section 6.3. The tables in this section use the notation Adjoint DAE to refer to the estimates developed from section 3 (theorems 3.2 to 3.5), and use Adjoint ODE to refer to the estimates developed from section 4 (theorems 4.1 and 4.2).

### 6.1 Semi-explicit Index-1 DAEs Examples

We begin with relatively simple, index-1 DAEs in semi-explicit form. 16

<!-- source-page: 17 -->

Example 6.1 The Robertson semi-explicit index-1 DAEs is ˙y1 = −0.04y1 + 104y2z, ˙y2 = 0.04y1 −104y2z −(3 × 107)y2 2, 0 = y1 + y2 + z −1,        (44) with the initial condition for the differential variable y(0) = [1, 0]T . The consistent initial condition for the algebraic variable is z(0) = 0 and t ∈(0, T]. This is a common example problem discussed in the documentation of existing numerical DAE solvers [64]. For this example, we focus on a QoI that is cumulative over time, Q[0,T ]. Below, we present the error estimate and effectivity ratios for two variations of Q[0,T ](y, z), one involving only the differential variables (table 1) and one involving only the algebraic variables (table 2). Both are cumulative over the interval [0, T], and computed using theorem 3.2 and theorem 4.1. We first set ψy(t) = [1, 1]T , ψz(t) = 0 and assess our error estimate using both the Adjoint DAE and Adjoint ODE approaches. The results are presented in table 1. We then repeat the experiment with ψz(t) = 1, ψy(t) = [0, 0]T and present the results in table 2. Both experiments were performed for multiple values of terminal time (T) and time step size of the original DAE (∆t). For clarity of presentation, we only report our results to 5 significant digits. The data in tables 1 and 2 indicates that the error estimates from both approaches are quite accurate, and effectivity ratio close to one, which illustrates the validation of our theorems. Moreover, the tables appear to indicate that there is no difference between the errors calculated using the adjoint DAE and adjoint ODE approaches. This is not true, strictly speaking, as the results corresponding to adjoint ODEs and Adjoint DAEs display a difference after the tenth digit (not shown). Table 1 Numerical Results for DAE in example 6.1 using Adjoint DAE (theorem 3.2), and Adjoint ODE (theorem 4.1) to estimate the error eQ[0,T ] where ψy(t) = [1, 1]T and ψz(t) = 0. ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 -2.8546e-06 -2.8546e-06 0.9989 0.9989 10 -6.4758e-05 -6.4758e-05 0.9999 0.9999 20 -1.2082e-04 -1.2082e-04 0.9999 0.9999 50 -2.3590e-04 -2.3590e-04 0.9999 0.9999 100 -3.5917e-04 -3.5917e-04 0.9999 0.9999 0.0005 1 -1.4288e-06 -1.4288e-06 0.9996 0.9996 10 -3.2384e-05 -3.2384e-05 0.9999 0.9999 20 -6.0415e-05 -6.0415e-05 1.0 1.0 50 -1.1796e-04 -1.1796e-04 1.0 1.0 100 -1.7960e-04 -1.7960e-04 1.0 1.0 For our next example, we again analyze an index-1 DAE in semi-explicit form, but with a nonlinear algebraic constraint. 17

<!-- source-page: 18 -->

Table 2 Numerical Results for DAE in example 6.1 using Adjoint DAE ( theorem 3.2), and Adjoint ODE (theorem 4.1) to estimate the error eQ[0,T ] where ψz(t) = 1 and ψy(t) = [0, 0]T . ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 2.8546e-06 2.8546e-06 0.9989 0.9989 10 6.4758e-05 6.4758e-05 0.9999 0.9999 20 1.2082e-04 1.2082e-04 0.9999 0.9999 50 2.3590e-04 2.3590e-04 0.9999 0.9999 100 3.5917e-04 3.5917e-04 0.9999 0.9999 0.0005 1 1.4288e-06 1.4288e-06 0.9996 0.9996 10 3.2384e-05 3.2384e-05 0.9999 0.9999 20 6.0415e-05 6.0415e-05 1.0 1.0 50 1.1796e-04 1.1796e-04 1.0 1.0 100 1.7960e-04 1.7960e-04 1.0 1.0 Example 6.2 The Pendulum semi-explicit index-1 DAEs [65] is ˙y1 = y3, ˙y2 = y4, m ˙y3 = −2y1z, m ˙y4 = −mg −2y2z, m  y2 3 + y2 4 −gy2  −2z  y2 1 + y2 2  = 0,                  (45) for t ∈(0, T]. Here the parameters are m = 1, g = 9.81, s = 1, and the initial condition for the differential variable is y(0) = [0, −s, 1, 0]T . The consistent initial condition for the algebraic variable is z(0) = m(1+s·g) 2s2 and t ∈(0, T]. For this example we discuss results for two variations of QoI at the terminal time, QT (see eq. (13)); one involving only the differential variables (table 3) and one involving only the algebraic variables (table 4). Error estimates for various values of the terminal time (T) and time step size (∆t) are computed using theorem 3.3 and theorem 4.2. In table 3 we show error estimates and effectivity ratios for the case when the QoI depends on the differential variables only, that is, QT (y, z) = (y(T), ζy), with ζy = [1, 1, 1, 1]T and ζz = 0. We show results for the case when the QoI depends on the algebraic variable only, QT (y, z) = (z(T), ζz), with ζz = 1 and ζy = [0, 0, 0, 0]T in table 4. Again, effectivity ratios demonstrates the accuracy of the error estimates.

### 6.2 Hessenberg (Pure) Index-2 DAEs Examples

We now move on to a nonlinear non-autonomous index-2 DAE in Hessenberg form. 18

<!-- source-page: 19 -->

Table 3 Numerical Results for DAE in example 6.2 using Adjoint DAE (theorem 3.3), and Adjoint ODE (theorem 4.2) to estimate the error eQT where ζy = [1, 1, 1, 1]T and ζz = 0. ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 -5.0252e-03 -5.0234e-03 0.9997 0.9993 2 9.1300e-03 9.1376e-03 0.9986 0.9994 3 -1.5065e-02 -1.5059e-02 0.9975 0.9972 4 1.6388e-02 1.6414e-02 1.0 1.002 5 -2.4788e-02 -2.4786e-02 0.9952 0.9951 0.0005 1 -2.5171e-03 -2.5166e-03 0.9999 0.9997 2 4.5715e-03 4.5734e-03 0.9993 0.9997 3 -7.5751e-03 -7.5738e-03 0.9988 0.9986 4 8.2010e-03 8.2074e-03 1.0 1.001 5 -1.2512e-02 -1.2511e-02 0.9976 0.9976 Table 4 Numerical Results for DAE in example 6.2 using Adjoint DAE (theorem 3.3), and Adjoint ODE (theorem 4.2) to estimate the error eQT where ζz = 1 and ζy = [0, 0, 0, 0]T . ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 5.0019e-03 5.0059e-03 0.9969 0.9977 2 9.8723e-03 9.8878e-03 0.9939 0.9954 3 1.4554e-02 1.4587e-02 0.9912 0.9934 4 1.8998e-02 1.9050e-02 0.9888 0.9915 5 2.3160e-02 2.3230e-02 0.9871 0.9901 0.0005 1 2.5094e-03 2.5104e-03 0.9984 0.9988 2 4.9689e-03 4.9728e-03 0.9969 0.9977 3 7.3475e-03 7.3556e-03 0.9956 0.9967 4 9.6163e-03 9.6293e-03 0.9944 0.9958 5 1.1749e-02 1.1766e-02 0.9936 0.9951 Example 6.3 The following system is a Hessenberg (pure) index-2 DAE ˙y1 = λy1 −z, ˙y2 = (2λ −sin2 t)y2 + (sin2 t)(y1 −1)2, 0 = y2 −(y1 −1)2,        (46) where λ is a parameter and the given initial condition corresponding to the differential variable is y(0) = [2, 1]T . The consistent initial condition for the algebraic variable is z(0) = λ and t ∈(0, T]. For this example, we place our attention on a QoI that is cumulative time, Q[0,T ] (see eq. (12)). For this experiment we set λ = 1. Once again, we present the error estimate and effectivity ratios for two variations of Q[0,T ], one involving only the 19

<!-- source-page: 20 -->

differential variables (table 5) and one involving only the algebraic variables (table 6). The error estimates are computed using theorem 3.4 and theorem 4.1. We first set ψy(t) = [1, 1]T , ψz(t) = 0 and asses our error estimate using both the Adjoint DAE and Adjoint ODE approaches in table 5. We then repeat the experiment with ψz(t) = 1, ψy(t) = [0, 0]T and present the results in table 6. Once again we see small error estimates and effectivity ratios very close to unity. The only exception is the error estimate using the adjoint ODE, where as the terminal time T increases, we see that the error estimate becomes slightly less accurate as indicated by the effectivity ratio. Table 5 Numerical Results for DAE in example 6.3 using Adjoint DAE (theorem 3.4), and Adjoint ODE (theorem 4.1) to estimate the error eQ[0,T ] where ψy(t) = [1, 1]T and ψz(t) = 0. ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 -5.6088e-04 -5.6076e-04 0.9999 0.9997 2 -1.0454e-03 -1.0473e-03 0.9978 0.9996 3 -1.2735e-03 -1.2912e-03 0.9859 0.9996 0.0005 1 -2.8053e-04 -2.8050e-04 1.0 0.9999 2 -5.2340e-04 -5.2389e-04 0.9989 0.9998 3 -6.4142e-04 -6.4583e-04 0.9989 0.9998 Table 6 Numerical Results for DAE in example 6.3 using Adjoint DAE (theorem 3.4), and Adjoint ODE (theorem 4.1) to estimate the error eQ[0,T ] where ψz(t) = 1 and ψy(t) = [0, 0]T . ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 3.1533e-04 3.1540e-04 0.9991 0.9993 2 4.2383e-04 4.3143e-04 0.9812 0.9988 3 4.2758e-04 4.7408e-04 0.9006 0.9985 0.0005 1 1.5785e-04 1.5786e-04 0.9995 0.9996 2 2.1404e-04 2.1594e-04 0.9906 0.9994 3 2.2564e-04 2.3730e-04 0.9502 0.9993 20

<!-- source-page: 21 -->

Example 6.4 The Pendulum index-2 DAE [65] system is ˙y1 = y3, ˙y2 = y4, m ˙y3 = −2y1z, m ˙y4 = −mg −2y2z, y1y3 + y2y4 = 0,                (47) for t ∈(0, T]. Here the parameters are m = 1, g = 9.81, s = 1, and the initial condition for the differential variable is y(0) = [0, −s, 1, 0]T . The consistent initial condition for the algebraic variable is z(0) = m(1+s·g) 2s2 and t ∈(0, T]. The pendulum index-2 DAEs in example 6.4 represent a Hessenberg index-2 problem. Here, we concentrate on the QoI at the terminal time, QT (see eq. (13)). We present in table 7 the error estimate and effectivity ratios for QT , involving both the differential variables and algebraic variables. The error estimates are computed using theorem 3.5 and theorem 4.2. The QoI QT is defined by setting ζy = [1, 1, 1, 1]T , ζz =

### 1. We observe promising effectivity ratios for both the Adjoint ODE and Adjoint DAE

approaches. Table 7 Numerical Results for DAE in example 6.4 using Adjoint DAE (theorem 3.5), and Adjoint ODE (theorem 4.2) to estimate the error eQT where ζy = [1, 1, 1, 1]T and ζz = 1. ∆t T Error Estimate Effectivity Ratio Adjoint ODEs Adjoint DAEs Adjoint ODEs Adjoint DAEs 0.001 1 -1.7159e-03 -1.7153e-03 1.003 1.002 2 1.5162e-02 1.5169e-02 0.9975 0.998 3 -5.5532e-03 -5.5430e-03 1.006 1.004 4 2.6268e-02 2.6288e-02 0.999 0.9997 5 -9.9657e-03 -9.9507e-03 1.002 1.0 0.0005 1 -8.5615e-04 -8.5598e-04 1.001 1.001 2 7.6081e-03 7.6099e-03 0.9988 0.999 3 -2.7685e-03 -2.7659e-03 1.003 1.002 4 1.3182e-02 1.3187e-02 0.9996 0.9999 5 -4.9932e-03 -4.9893e-03 1.001 0.9999

### 6.3 Electro-Neutral Nernst-Planck Equation of Ion Transport

Example 6.5 We consider a system describing the evolution of the concentrations of two monovalent ions. This system is sometimes called the Electro-Neutral Nernst-Planck 21

<!-- source-page: 22 -->

Equations (ENNPE) [3, 66]. The evolution equations and constraint are written as ∂c ∂t = Dc  ∂2c ∂x2 + ∂ ∂x  c∂Ψ ∂x  , ∂a ∂t = Da  ∂2a ∂x2 −∂ ∂x  a∂Ψ ∂x  , 0 = c −a,                (48) where c(x, t) and a(x, t) denote the concentration of Hydrogen ion (cation) and Chloride ion (anion) respectively, and ∂Ψ ∂x (x, t) is the electric potential gradient. No flux (homogeneous Robin) boundary conditions are given by ∂c ∂x + c∂Ψ ∂x

x=0 = ∂c ∂x + c∂Ψ ∂x

x=1 = 0, ∂a ∂x −a∂Ψ ∂x

x=0 = ∂a ∂x −a∂Ψ ∂x

x=1 = 0.      (49) Initial conditions are c(x, 0) = a(x, 0) = 2 + cos(πx) and x ∈[0, 1], t ∈(0, T], where Dc, Da are the diffusion coefficients of the cation and anion ions respectively. The method of separation of variables gives the analytic solution c(x, t) = a(x, t) = 2 + e−π2Defft cos(πx), (50) w(x, t) = Da −Dc Da + Dc  −πe−π2Defft sin(πx) 2 + e−π2Defft cos(πx), (51) where Deff = 2DcDa Dc + Da , and w = ∂Ψ ∂x . Notice that the electric potential Ψ is only defined up to an additive constant. Therefore we utilize w = ∂Ψ ∂x as our state variable.

#### 6.3.1 Spatial discretization: Staggered Grid Approach

We use a staggered grid to discretize the spatial derivatives. This technique has been used in many numerical methods (particularly in computational fluid dynamics) since the development of the Marker and Cell (MAC) method [67]. Consider a set of Ns −1 uniformly spaced grid points in the spatial domain with spacing ∆x. For the unit interval let, ˜xi = i∆x, i = 1, 2, . . . , Ns −1, ∆x = 1 Ns . These points are often called “cell edges” and are the locations where we represent vector valued quantities such as the electric potential gradient w(˜xi, t). We also introduce a second spatial grid at the so-called “cell centers” xj = (2j −1)∆x/2, j = 1, 2, . . . , Ns. These points will be used to represent the values of scalar valued quantities such as the ion concentrations (c(xj, t) and a(xj, t)). This staggered grid facilitates the 22

<!-- source-page: 23 -->

use of centered finite difference approximations to the various spatial derivatives in eq. (48) and representation of the no flux boundary conditions eq. (49), and leads to the approximation: Cj(t) ≈c(xj, t), Aj(t) ≈a(xj, t), and Wi(t) ≈w(˜xi, t). Details of the staggered grid approach are given in appendix B. Spatial disretization converts the ENNPE to a Hessenberg index-2 DAE, ˙C = DcMC + DcBC, ˙A = DaMA −DcBA, 0 = Π(C) −Π(A),      (52) where, M = 1 ∆x2        −1 1 0 · · · 0 1 −2 1 · · · 0 0 1 −2 · · · 0 ... ... ... ... ... 0 0 0 · · · −1        , BC = 1 2∆x        (C1 + C2)W1 (C2 + C3)W2 −(C1 + C2)W1 (C3 + C4)W3 −(C2 + C3)W2 ... −(CNs−1 + CNs)WNs−1        , BA = 1 2∆x        (A1 + A2)W1 (A2 + A3)W2 −(A1 + A2)W1 (A3 + A4)W3 −(A2 + A3)W2 ... −(ANs−1 + CNs)WNs−1        , C =      C1 C2 ... CNs     , A =      A1 A2 ... ANs     , and W =      W1 W2 ... WNs−1     , Π(ξ) =      ξ2 ξ3 ... ξNs     for ξ =      ξ1 ξ2 ... ξNs     , where M ∈RNs×Ns, and BC, BA, C(t), A(t), ξ(t) ∈RNs, and W(t) ∈RNs−1. We set the differential variables as y = [CT , AT ]T , and algebraic variables as z = W, with n = 2Ns, and m = Ns −1, then eq. (52) is exactly in the form of eq. (4). Initial conditions corresponding to the differential variables are given by Cj(0) = Aj(0) = 2 + cos (πxj), for j = 1, 2, 3, . . . , Ns. There is a subtle point to be made with regards to the initial condition for the electric potential gradient (the algebraic variable). For the PDE system eq. (48), one can obtain the initial condition by differentiating the constraint equation, substituting the transport equations to eliminate ∂c ∂t and ∂a ∂t , solving for w(x, t) (this calculation is used to derive eq. (51)) and evaluating at t = 0 to yield w(x, 0) = Dc ∂c ∂x −Da ∂a ∂x Dcc + Daa

t=0 . (53) 23

<!-- source-page: 24 -->

This expression can then be evaluated at the points ˜xi to derive what we call the “analytic initial condition” for the algebraic variables Wi. Alternately, one can perform a similar calculation on the spatially discretized DAE system eq. (52): differentiate the constraint equation, eliminate ˙C and ˙A, solve for W and set t = 0. Doing so leads to what we call the “discrete initial condition” corresponding to the algebraic variables Wi, Wl(0) = Dc  Cl−Cl+1 ∆x  −Da  Al−Al+1 ∆x  Dc  Cl+Cl+1 2  + Da  Al+Al+1 2 

t=0, for l = 1, 2, 3, · · · , Ns −1. (54) Notice that eq. (54) is equivalent to a relatively simple centered finite difference approximation to eq. (53). They are not equivalent, but differ by the spatial discretization error. This does raise interesting questions about the appropriate initial conditions that one should utilize when time-evolving discretized PDAEs, and indicates a potential line of future inquiry. In our numerical experiments, we used both the discrete initial condition and analytic initial condition for algebraic variables, and observed no appreciable difference in the error analysis that is the focus of this paper. For brevity we present only the results obtained using the discrete initial condition.

#### 6.3.2 Error analysis of the ENNPE model

For this semi-discretized PDAE (ENNPE) eq. (52), we focus on the QoI at the terminal time, QT (see eq. (13)). We present the error estimate based on Adjoint DAE and effectivity ratios for two variations of QT , one involving only the differential variables (column corresponding to  e(y)(T), ζy in table 8) and one involving only the algebraic variables (column corresponding to  e(z)(T), ζz in table 8). The error in the QoI QT involving both the differential and algebraic state variables at t = T is estimated using Adjoint DAE (theorem 3.5). We choose the spatial grid spacing ∆x = 0.004, which is small enough so that the error due to spatial discretization is negligible relative to the error due to temporal discretization. The dimension of the resulting nonlinear Hessenberg index-2 DAE is 749. We are not performing Adjoint ODE based error estimation for this particular PDAE because of its too high computation cost to obtain the corresponding index reduction ODE system. The semidiscretized system in eq. (52) corresponds to differential variables y = [CT , AT ]T , and algebraic variables z = W. The values used for the diffusion coefficients are Dc = 0.5, and Da = 0.05. To estimate the error  e(y)(T), ζy (using theorem 3.5) involving only the differential variables y at t = T, we set ζy = [1Ns, 1Ns]T , where 1Ns = [1, 1, . . . , 1] ∈RNs is a column vector of ones (we also set ζz = [0Ns−1]T , where 0Ns−1 = [0, 0, . . . , 0] ∈RNs−1 is a column vector of zeros). Similarly, to evaluate  e(z)(T), ζz using theorem 3.5), we set ζz = [1Ns−1]T , and ζy = [0Ns, 0Ns]T . The reference error is computed using the analytical solution eqs. (50) and (51) evaluated at terminal time and the results are presented in table 8 We notice that the estimates of error  e(z)(T), ζz are quite accurate whereas those for the error  e(y)(T), ζy demonstrate somewhat anomalous results. The effectivity 24

<!-- source-page: 25 -->

ratios for this latter case are sometimes not close to one. In precisely these cases, the errors are extremely small (within a couple of orders of magnitude of machine precision), and hence incur catastrophic floating point cancellation in their calculation. To illustrate this, we split the integral ⟨ϕ(y), f(Y, Z)−˙Y ⟩into four integrals as follows: ⟨ϕ(y), f(Y, Z) −˙Y ⟩= I1 + I2 + I3 + I4, where Ii = ⟨ϕ(y) i , ˜fi⟩, each of ϕ(y) i ’s, ˜fi’s are vectors of same size (125) for i = 1, 2, 3, 4 and analogously ϕ(y) = [ϕ(y) 1 , ϕ(y) 2 , ϕ(y) 3 , ϕ(y) 4 ]T , and f(Y, Z) −˙Y = [ ˜f1, ˜f2, ˜f3, ˜f4]T . We present the values for Ii in table 9 and observe the values of these integrals match up to 11 or 12 digits, while having opposite signs. This is the cause of catastrophic cancellation in the calculation of the sum I1+I2+I3+I4. To illustrate the effectiveness of our error estimate while avoiding this issue, we estimate the error using QoIs that isolate only the negative (or alternately, positive) components of the error. To this end, we define  e(y)(T), ζy −  , (the −subscript indicates negative error) by setting ζy −= [1125, 0125, 1125, 0125]T . This isolates the error in both differential variables in the left half of the spatial domain (where we observe the errors with negative sign). The results for this case are in table 10, and indicate that the effectivity ratio is close to one, as expected. We observe similar results for  e(y)(T), ζy +  , (the + subscript indicates positive error) when setting ζy + = [0125, 1125, 0125, 1125]T as shown in table 10. Table 8 Numerical Results for DAE in example 6.5 using Adjoint DAE (theorem 3.5) to estimate the error eQT where ζy = [1250, 1250]T , ζz = [0249]T and again eQT where ζz = [1249]T , ζy = [0250, 0250]T with spatial grid spacing ∆x = 0.004, and ∆t = 0.001. T eQT =  e(y)(T), ζy eQT =  e(z)(T), ζz Error Estimate Effectivity Ratio Error Estimate Effectivity Ratio 0.5 3.1247e-12 1.168 -2.9255e-02 1.008 1 4.1497e-12 0.9014 -3.5010e-02 0.9881 2 8.8735e-12 1.173 -2.7558e-02 0.9795 3 2.4128e-12 1.025 -1.6760e-02 0.9769

## 7 Conclusions

In this paper, we propose a novel technique for a posteriori error estimates for numerical solution of DAEs. In particular, our technique may be used to assess error for QoIs involving the differential or algebraic state variables, and that are cumulative in time, or evaluated at the terminal time. Furthermore, our methodology may be applied to the semi-explicit index-1 or Hessenberg index-2 DAEs. Our technique is based on the formulation and solution of an adjoint DAE, which is a linear problem, making it relatively cost effective to implement. We also present a second technique which is based on an adjoint ODE. This second technique, while being conceptually simpler, 25

<!-- source-page: 26 -->

Table 9 Numerical Results for DAE in example 6.5 using theorem 3.5 to investigate the reason behind the catastrophic cancellation occurs in eQT =  e(y)(T), ζy at T with spatial grid spacing ∆x = 0.004, and ∆t = 0.001. T Integrals Approximate Values 0.5 I1 -0.012900368135421083 I2 0.012900368138223206 I3 -0.012900368138363746 I3 0.012900368138686344 Table 10 Numerical Results for DAE in example 6.5 using Adjoint DAE (theorem 3.5 with ζz = [0249]T ) to estimate the error  e(y)(T), ζy −  where ζy −= [1125, 0125, 1125, 0125]T and  e(y)(T), ζy +  where ζy + = [0125, 1125, 0125, 1125]T with spatial grid spacing ∆x = 0.004. ∆t T Error  e(y)(T), ζy −  Error  e(y)(T), ζy +  Error estimate Effectivity Ratio Error estimate Effectivity Ratio 0.001 0.5 -2.0443e-02 0.9715 2.0443e-02 0.9715 1 -2.6109e-02 0.9716 2.6109e-02 0.9716 2 -2.1295e-02 0.9716 2.1295e-02 0.9716 3 -1.3026e-02 0.9717 1.3026e-02 0.9717 0.002 0.5 -4.0866e-02 0.9856 4.0866e-02 0.9856 1 -5.2201e-02 0.9857 5.2201e-02 0.9857 2 -4.2588e-02 0.9858 4.2588e-02 0.9858 3 -2.6058e-02 0.9859 2.6058e-02 0.9859 is more computationally more expensive. We tested these two techniques numerically for various types of index-1 and Hessenberg index-2 DAE problems: linear, nonlinear, autonomous, non-autonomous, and an example PDAE. In both techniques we have the accurate error estimate and the effectivity ratio close to one, unless there was catastrophic cancellation resulting in both the computed and exact error being extremely small. The adjoint ODE approach is too costly for a large scale problem such as PDAEs, due to the cost of order reduction for large scale systems. However, the adjoint DAE approach works extremely well in this case, without the associated cost. There are a number of future directions which arise from this work. One such direction is extending the analysis to partial differential algebraic equations in such a way that the estimates identify the error contribution due to the spatial and temporal discretizations, as was done for a PDE in [37]. Another direction is deriving adaptive algorithms based on the a posteriori estimates. This requires a careful analysis of the numerical scheme under consideration to quantify the effects of different quadratures, 26

<!-- source-page: 27 -->

time-stepping choices, projection operators, etc. Such analysis for ODEs and PDEs have been carried out in [33, 34, 38, 39, 68], and in future we aim to utilize these ideas to extend the analysis in this work. Appendix A Some Proofs Proof of lemma 3.1 Multiplying eq. (16a) by the error term e(y) and eq. (16b) by the error term e(z) and integrating by parts, eQ[0,T ] = ⟨−˙ϕ(y), y −Y ⟩−⟨¯fT y ϕ(y), y −Y ⟩−⟨¯gT y ϕ(z), y −Y ⟩−⟨¯fT z ϕ(y), z −Z⟩ −⟨¯gT z ϕ(z), z −Z⟩ (A1) Considering the first term on the right hand side of eq. (A1) and applying integration by parts, ⟨−˙ϕ(y), y −Y ⟩= Z T 0  ˙ϕ(y)(t), y(t) −Y (t)  dt = N−1 X k=0 Z tk+1 tk  ˙ϕ(y)(t), y(t) −Y (t)  dt = N−1 X k=0 Z tk+1 tk  ϕ(y)(t), ˙y(t) −˙Y (t)  dt + N−1 X k=0 h ϕ(y)(tk), y(tk) −Y (tk)  −  ϕ(y)(tk+1), y(tk+1) −Y (tk+1) i , = N−1 X k=0 Z tk+1 tk  ϕ(y)(t), ˙y(t) −˙Y (t)  dt +  ϕ(y)(t0), y(t0) −Y (t0)  −  ϕ(y)(tN), y(tN) −Y (tN)  , = ⟨ϕ(y), ˙y −˙Y ⟩+  ϕ(y)(0), y(0) −Y (0)  −  ϕ(y)(T), y(T) −Y (T)  , (A2) where we also used the fact that all functions under consideration (ϕ, y, Y ) are continuous on [0, T]. Using eq. (A2) in eq. (A1), eQ[0,T ] = ⟨ϕ(y), ˙y −˙Y ⟩−⟨ϕ(y), ¯fy(y −Y ) + ¯fz(z −Z)⟩−⟨ϕ(z), ¯gy(y −Y ) + ¯gz(z −Z)⟩ +  ϕ(y)(0), y(0) −Y (0)  −  ϕ(y)(T), y(T) −Y (T)  . (A3) Now using the properties eq. (18) and eq. (19) followed by using eq. (1), eQ[0,T ] = ⟨ϕ(y), ˙y −˙Y ⟩−⟨ϕ(y), f(y, z) −f(Y, Z)⟩−⟨ϕ(z), g(y, z) −g(Y, Z)⟩ +  ϕ(y)(0), y(0) −Y (0)  −  ϕ(y)(T), y(T) −Y (T)  , = ⟨ϕ(y), ˙y −f(y, z)⟩−⟨ϕ(y), ˙Y −f(Y, Z)⟩+ ⟨ϕ(z), g(Y, Z)⟩+  ϕ(y)(0), y(0) −Y (0)  −  ϕ(y)(T), y(T) −Y (T)  , =  ϕ(y)(0), e(y)(0)  −  ϕ(y)(T), y(T) −Y (T)  + ⟨ϕ(y), f(Y, Z) −˙Y ⟩+ ⟨ϕ(z), g(Y, Z)⟩. □ 27

<!-- source-page: 28 -->

Proof of lemma 3.2 1.  P T ζy, e(y) =  I −¯gT y ( ¯f T z ¯gT y )−1 ¯f T z  ζy, e(y) , =  ζy, e(y) −  ¯gT y ( ¯f T z ¯gT y )−1 ¯f T z ζy, e(y) , =  ζy, e(y) −  ( ¯f T z ¯gT y )−1 ¯f T z ζy, ¯gye(y) , =  ζy, e(y) +  ( ¯f T z ¯gT y )−1 ¯f T z ζy, g(Y )  . 2.  −P T ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, e(y) , =  −  I −¯gT y ( ¯f T z ¯gT y )−1 ¯f T z  ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, e(y) , =  −¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, e(y) +  ¯gT y ( ¯f T z ¯gT y )−1 ¯f T z ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, e(y) , = −  ¯gT y ( ¯f T z ¯gT y )−1ζz, ¯fye(y) +  ( ¯f T z ¯gT y )−1 ¯f T z ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, ¯gye(y) , = −  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(y, z) −f(Y, Z) −¯fz(z −Z)  +  ( ¯f T z ¯gT y )−1 ¯f T z ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, g(y) −g(Y )  , = −  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(y, z)  +  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(Y, Z)  +  ¯gT y ( ¯f T z ¯gT y )−1ζz, ¯fz(z −Z)  −  ( ¯f T z ¯gT y )−1 ¯f T z ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, g(Y )  , = −  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(y, z)  +  ¯gT y ( ¯f T z ¯gT y )−1ζz, f(Y, Z)  +  ζz, e(z) −  ( ¯f T z ¯gT y )−1 ¯f T z ¯f T y ¯gT y ( ¯f T z ¯gT y )−1ζz, g(Y )  . 3.

d¯gT y dt   ¯f T z ¯gT y −1 ζz, e(y) ! , =   ¯f T z ¯gT y −1 ζz, d¯gy dt e(y)  , =   ¯f T z ¯gT y −1 ζz, d[¯gye(y)] dt −¯gy dey dt  , =   ¯f T z ¯gT y −1 ζz, −dg(Y ) dt −¯gy[f(y, z) −˙Y ]  , = −   ¯f T z ¯gT y −1 ζz, dg(Y ) dt  −   ¯f T z ¯gT y −1 ζz, ¯gyf(y, z)  +   ¯f T z ¯gT y −1 ζz, ¯gy ˙Y  , = −   ¯f T z ¯gT y −1 ζz, dg(Y ) dt  −  ¯gT y   ¯f T z ¯gT y −1 ζz, f(y, z)  +  ¯gT y   ¯f T z ¯gT y −1 ζz, ˙Y  . 28

<!-- source-page: 29 -->

□ Appendix B Staggered Grid Discretization We use relatively standard central difference approximations for the spatial derivative of cx, c, ax, and a. The nonlinear terms cw, and aw, require multiplication of quantities which “live” at cell centers and those that live at cell edges. In this case, we average the two cell centered quantities (c or a) to the cell edge between. We explicitly show the details of the spatial discretization for c below. The discretization of a is completely analogous. The partial derivative of c with respect to x at ˜xj is approximated as follows: cx(˜xj) ≈c(˜xj + ∆x/2) −c(˜xj −∆x/2) ∆x = c(xj+1) −c(xj) ∆x . That is to say that first derivatives (which naturally live at cell edges) are calculated by applying centered differences to quantities defined at cell centers. For the nonlinear terms, we average concentrations to the cell edges to yield c(˜xj)w( ˜xj) ≈c(˜xj + ∆x/2) + c(˜xj −∆x/2) 2 w(˜xj) = c(xj+1) + c(xj) 2 w(˜xj) (B4) We can now apply centered differences to the above expressions to yield the following expressions for j = 2, 3, . . . , Ns −1, ∂ ∂x (cx + cw)

xj ≈ 1 ∆x (cx(xj + ∆x/2) + c(xj + ∆x/2)w(xj + ∆x/2)) −1 ∆x (cx(xj −∆x/2) + c(xj −∆x/2)w(xj −∆x/2)) , = 1 ∆x (cx(˜xj) + c(˜x)w(˜xj)) −1 ∆x (cx(˜xj−1) + c(˜xj−1)w(˜xj−1)) , = 1 ∆x c(xj+1) −c(xj) ∆x + c(xj+1) + c(xj) 2 w(˜xj)  −1 ∆x c(xj) −c(xj−1) ∆x + c(xj) + c(xj−1) 2 w(˜xj−1)  = 1 ∆x2 (c(xj+1) −2c(xj) + c(xj−1)) + 1 2∆x  (c(xj) + c(xj+1)) w(˜xj) −(c(xj) + c(xj−1)) w(˜xj−1)  . 29

<!-- source-page: 30 -->

For j = 1 and j = Ns, we need to utilize the no flux (homogeneous Robin) boundary conditions eq. (49). These can be expressed as cx + cw|x=0 = cx + cw|˜x0 = 0, and cx + cw|x=1 = cx + cw|˜xNs = 0. Now, for j = 1, i.e., the scheme at the left boundary of the modified domain is ∂ ∂x (cx + cw)

x1 ≈ 1 ∆x  cx(˜x1) + c(˜x1)w(˜x1)  −  cx(˜x0) + c(˜x0)w(˜x0)  , = 1 ∆x (cx(˜x1) + c(˜x1)w(˜x1)) −0, = 1 ∆x c(x2) −c(x1) ∆x + c(x2) + c(x1) 2 w(˜x1)  = 1 ∆x2 (c(x2) −c(x1))) + 1 2∆x  (c(x1) + c(x2)) w(˜x1)  . Similarly, for j = Ns, i.e., the scheme at the right boundary of the modified domain is ∂ ∂x (cx + cw)

xNs ≈ 1 ∆x  cx(˜xNs) + c(˜xNs)w(˜xNs)  −  cx(˜xNs−1) + c(˜xNs−1)w(˜xNs−1)  , = 0 −1 ∆x (cx(˜xNs−1) + c(˜xNs−1)w(˜xNs−1)) , = −1 ∆x c(xNs) −c(xNs−1) ∆x + c(xNs) + c(xNs−1) 2 w(˜xNs−1)  = 1 ∆x2 (−c(xNs) + c(xNs−1)) + 1 2∆x  −(c(xNs) + c(xNs−1)) w(˜xNs−1)  . A completely analogous discretization is used for the the anion a. These finite difference discretizations are used to construct the right hand side of the differential equation for the differential variables in eq. (52). In order to construct the algebraic constraint for eq. (52) we notice that the above finite difference equations are conservative. This implies that Ns X j=1 c(xj, t) and Ns X j=1 a(xj, t), are both constants independent of time. This, in turn, means that if c(xj, 0)−a(xj, 0) = 0 at the initial time, and c(xj) −a(xj) = 0 for j = 2, 3, . . . Ns, then it must be true 30

<!-- source-page: 31 -->

that c(x1) −a(x1) = 0. Put another way, if we use a conservative discretization and use initial conditions which satisfy the constraint at all spatial locations, then we do not need to explicitly enforce the constraint at all locations. We need only enforce it in Ns −1 grid cells, and we are guaranteed that it will be satisfied in the remaining grid cell “for free”. Thus, we do not explicitly require that C −A = 0 in eq. (52). Rather, we require that Π(C −A) = 0, where Π is the linear operator which simply evaluates a variable at all but the first cell center.
