# -*- coding: utf-8 -*-
"""Am (M1)

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1SKUizQN1tn5mdPkd80eYac4njXfBiruF

### **Required package installations**
"""

pip install scikit-optimize

pip install optuna

"""### **Weight Optimization**"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.neighbors import KNeighborsRegressor
from skopt import gp_minimize
from skopt.space import Real

# pipeline creation for ensemble model that contains all the considered algorithm with tunned hyperparameters
model_definitions = {
    'SVR': Pipeline([
        ('scaler', StandardScaler()),
        ('model', SVR(C=1000, epsilon=1.0, gamma=0.0007665189689585275, kernel='rbf'))
    ]),
    'RandomForest': Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor(bootstrap=True, max_depth=30, min_samples_leaf=1,
                                        min_samples_split=3, n_estimators=300, random_state=42))
    ]),
    'ExtraTrees': Pipeline([
        ('scaler', StandardScaler()),
        ('model', ExtraTreesRegressor(bootstrap=True, max_depth=5, min_samples_leaf=1,
                                      min_samples_split=2, n_estimators=50, random_state=42))
    ]),
    'GaussianProcess': Pipeline([
        ('scaler', StandardScaler()),
        ('model', GaussianProcessRegressor(alpha=0.07653054285055239, n_restarts_optimizer=10))
    ]),
    'KNN': Pipeline([
        ('scaler', StandardScaler()),
        ('model', KNeighborsRegressor(n_neighbors=3, p=1, weights='uniform'))
    ])
}

# Dataset Preparation
data = pd.read_csv('/content/HTSMA_DATA.csv')
X = data.iloc[:, 1:7]
ya = data.iloc[:, 18]

X_train, X_test, y_train, y_test = train_test_split(X, ya, test_size=0.2, random_state=42)

# Optmization through K-cross validation
kf = KFold(n_splits=5, shuffle=True, random_state=42)

def evaluate_ensemble(weights):
    rf_weight, svr_weight, et_weight, gp_weight, knn_weight = weights
    y_train_pred_ensemble = np.zeros_like(y_train, dtype=float)
    y_test_pred_ensemble = np.zeros_like(y_test, dtype=float)

    for train_idx, valid_idx in kf.split(X_train):

        X_train_fold, X_valid_fold = X_train.iloc[train_idx], X_train.iloc[valid_idx]
        y_train_fold, y_valid_fold = y_train.iloc[train_idx], y_train.iloc[valid_idx]


        fold_train_predictions = {}
        fold_test_predictions = {}
        for model_name in model_definitions:
            model = model_definitions[model_name]
            model.fit(X_train_fold, y_train_fold)
            y_valid_pred = model.predict(X_valid_fold)
            y_test_pred = model.predict(X_test)

            fold_train_predictions[model_name] = y_valid_pred
            fold_test_predictions[model_name] = y_test_pred


        fold_train_ensemble = (rf_weight * fold_train_predictions['RandomForest'] +
                               svr_weight * fold_train_predictions['SVR'] +
                               et_weight * fold_train_predictions['ExtraTrees'] +
                               gp_weight * fold_train_predictions['GaussianProcess'] +
                               knn_weight * fold_train_predictions['KNN'])

        fold_test_ensemble = (rf_weight * fold_test_predictions['RandomForest'] +
                              svr_weight * fold_test_predictions['SVR'] +
                              et_weight * fold_test_predictions['ExtraTrees'] +
                              gp_weight * fold_test_predictions['GaussianProcess'] +
                              knn_weight * fold_test_predictions['KNN'])

        y_train_pred_ensemble[valid_idx] = fold_train_ensemble
        y_test_pred_ensemble += fold_test_ensemble / kf.n_splits


    val_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred_ensemble))
    return val_rmse

# Bayesian Optimization to find optimal weights
search_space = [
    Real(0, 1, name='rf_weight'),
    Real(0, 1, name='svr_weight'),
    Real(0, 1, name='et_weight'),
    Real(0, 1, name='gp_weight'),
    Real(0, 1, name='knn_weight')
]

def objective(weights):

    normalized_weights = [w / sum(weights) for w in weights]
    return evaluate_ensemble(normalized_weights)

result = gp_minimize(objective, search_space, n_calls=50, random_state=42)
optimal_weights = [w / sum(result.x) for w in result.x]


rf_weight, svr_weight, et_weight, gp_weight, knn_weight = optimal_weights
y_train_pred_ensemble = np.zeros_like(y_train, dtype=float)
y_test_pred_ensemble = np.zeros_like(y_test, dtype=float)

for train_idx, valid_idx in kf.split(X_train):
    X_train_fold, X_valid_fold = X_train.iloc[train_idx], X_train.iloc[valid_idx]
    y_train_fold, y_valid_fold = y_train.iloc[train_idx], y_train.iloc[valid_idx]

    fold_train_predictions = {}
    fold_test_predictions = {}
    for model_name in model_definitions:
        model = model_definitions[model_name]
        model.fit(X_train_fold, y_train_fold)
        y_valid_pred = model.predict(X_valid_fold)
        y_test_pred = model.predict(X_test)

        fold_train_predictions[model_name] = y_valid_pred
        fold_test_predictions[model_name] = y_test_pred

    fold_train_ensemble = (rf_weight * fold_train_predictions['RandomForest'] +
                           svr_weight * fold_train_predictions['SVR'] +
                           et_weight * fold_train_predictions['ExtraTrees'] +
                           gp_weight * fold_train_predictions['GaussianProcess'] +
                           knn_weight * fold_train_predictions['KNN'])

    fold_test_ensemble = (rf_weight * fold_test_predictions['RandomForest'] +
                          svr_weight * fold_test_predictions['SVR'] +
                          et_weight * fold_test_predictions['ExtraTrees'] +
                          gp_weight * fold_test_predictions['GaussianProcess'] +
                          knn_weight * fold_test_predictions['KNN'])

    y_train_pred_ensemble[valid_idx] = fold_train_ensemble
    y_test_pred_ensemble += fold_test_ensemble / kf.n_splits

# Calculate RMSE and R² for the training and testing set
train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred_ensemble))
train_r2 = r2_score(y_train, y_train_pred_ensemble)
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred_ensemble))
test_r2 = r2_score(y_test, y_test_pred_ensemble)

print(f"Optimal Weights: RF = {rf_weight:.4f}, SVR = {svr_weight:.4f}, ET = {et_weight:.4f}, GP = {gp_weight:.4f}, KNN = {knn_weight:.4f}")
print(f"Training Set - RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")
print(f"Testing Set - RMSE: {test_rmse:.4f}, R²: {test_r2:.4f}")

"""### **Performance of Weight optimized model**"""

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.gaussian_process import GaussianProcessRegressor


model_definitions = {
    'SVR': Pipeline([
        ('scaler', StandardScaler()),
        ('model', SVR(C=1000, epsilon=1.0, gamma=0.0007665189689585275, kernel='rbf'))
    ]),
    'RandomForest': Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor(bootstrap=True, max_depth=30, min_samples_leaf=1,
                                        min_samples_split=3, n_estimators=300, random_state=42))
    ]),
    'ExtraTrees': Pipeline([
        ('scaler', StandardScaler()),
        ('model', ExtraTreesRegressor(bootstrap=True, max_depth=5, min_samples_leaf=1,
                                      min_samples_split=2, n_estimators=50, random_state=42))
    ]),
    'GaussianProcess': Pipeline([
        ('scaler', StandardScaler()),
        ('model', GaussianProcessRegressor(alpha=0.07653054285055239, n_restarts_optimizer=10))
    ]),
    'KNN': Pipeline([
        ('scaler', StandardScaler()),
        ('model', KNeighborsRegressor(n_neighbors=3, p=1, weights='uniform'))
    ])
}

optimal_weights = [0.0, 0.0000, 0.2928, 0.7072, 0.0000]
knn_weight, svr_weight, rfr_weight, et_weight, gp_weight = optimal_weights

kf = KFold(n_splits=5, shuffle=True, random_state=42)

y_train_pred_ensemble = np.zeros_like(y_train, dtype=float)
y_test_pred_ensemble = np.zeros_like(y_test, dtype=float)

for train_idx, valid_idx in kf.split(X_train):
    X_train_fold, X_valid_fold = X_train.iloc[train_idx], X_train.iloc[valid_idx]
    y_train_fold, y_valid_fold = y_train.iloc[train_idx], y_train.iloc[valid_idx]

    fold_train_predictions = {}
    fold_test_predictions = {}

    for model_name in model_definitions:
        model = model_definitions[model_name]
        model.fit(X_train_fold, y_train_fold)
        y_valid_pred = model.predict(X_valid_fold)
        y_test_pred = model.predict(X_test)

        fold_train_predictions[model_name] = y_valid_pred
        fold_test_predictions[model_name] = y_test_pred

    fold_train_ensemble = (knn_weight * fold_train_predictions['KNN'] +
                           svr_weight * fold_train_predictions['SVR'] +
                           rfr_weight * fold_train_predictions['RandomForest'] +
                           et_weight * fold_train_predictions['ExtraTrees'] +
                           gp_weight * fold_train_predictions['GaussianProcess'])

    fold_test_ensemble = (knn_weight * fold_test_predictions['KNN'] +
                          svr_weight * fold_test_predictions['SVR'] +
                          rfr_weight * fold_test_predictions['RandomForest'] +
                          et_weight * fold_test_predictions['ExtraTrees'] +
                          gp_weight * fold_test_predictions['GaussianProcess'])

    y_train_pred_ensemble[valid_idx] = fold_train_ensemble
    y_test_pred_ensemble += fold_test_ensemble / kf.n_splits

train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred_ensemble))
train_r2 = r2_score(y_train, y_train_pred_ensemble)
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred_ensemble))
test_r2 = r2_score(y_test, y_test_pred_ensemble)

print(f"Training Set - RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")
print(f"Testing Set - RMSE: {test_rmse:.4f}, R²: {test_r2:.4f}")

train_sigma = np.std(y_train - y_train_pred_ensemble)
test_sigma = np.std(y_test - y_test_pred_ensemble)

mean_sigma = (train_sigma + test_sigma) / 2
decision_line_x = np.linspace(min(min(y_train), min(y_test)), max(max(y_train), max(y_test)), 100)
decision_line_y = decision_line_x
upper_sigma = decision_line_y + mean_sigma
lower_sigma = decision_line_y - mean_sigma
upper_2sigma = decision_line_y + 2 * mean_sigma
lower_2sigma = decision_line_y - 2 * mean_sigma

plt.figure(figsize=(10, 6))
plt.fill_between(decision_line_x, lower_2sigma, upper_2sigma, color='yellow', alpha=0.5, label='±2σ')
plt.fill_between(decision_line_x, lower_sigma, upper_sigma, color='orange', alpha=0.5, label='±σ')
plt.scatter(y_train, y_train_pred_ensemble, color='blue', label='Training Data')
plt.scatter(y_test, y_test_pred_ensemble, color='green', label='Testing Data')
plt.plot(decision_line_x, decision_line_y, color='brown', linestyle='--', label='Decision Line (y=x)')
plt.xlabel('Actual Values')
plt.ylabel('Predicted Values')
plt.title('Ensemble Model Predictions vs Actual Values with Uncertainty Bands')
plt.legend()
plt.show()

max_len = max(len(y_train), len(y_train_pred_ensemble), len(y_test), len(y_test_pred_ensemble), len(decision_line_x))
y_train_padded = np.pad(y_train, (0, max_len - len(y_train)), constant_values=np.nan)
y_train_pred_padded = np.pad(y_train_pred_ensemble, (0, max_len - len(y_train_pred_ensemble)), constant_values=np.nan)
y_test_padded = np.pad(y_test, (0, max_len - len(y_test)), constant_values=np.nan)
y_test_pred_padded = np.pad(y_test_pred_ensemble, (0, max_len - len(y_test_pred_ensemble)), constant_values=np.nan)
decision_line_x_padded = np.pad(decision_line_x, (0, max_len - len(decision_line_x)), constant_values=np.nan)
decision_line_y_padded = np.pad(decision_line_y, (0, max_len - len(decision_line_y)), constant_values=np.nan)
upper_sigma_padded = np.pad(upper_sigma, (0, max_len - len(upper_sigma)), constant_values=np.nan)
lower_sigma_padded = np.pad(lower_sigma, (0, max_len - len(lower_sigma)), constant_values=np.nan)
upper_2sigma_padded = np.pad(upper_2sigma, (0, max_len - len(upper_2sigma)), constant_values=np.nan)
lower_2sigma_padded = np.pad(lower_2sigma, (0, max_len - len(lower_2sigma)), constant_values=np.nan)

plot_data = pd.DataFrame({
    'Prediction Train': y_train_pred_padded,
    'Actual Train': y_train_padded,
    'Prediction Test': y_test_pred_padded,
    'Actual Test': y_test_padded,
    'Decision Line X': decision_line_x_padded,
    'Decision Line Y': decision_line_y_padded,
    'Upper Sigma': upper_sigma_padded,
    'Lower Sigma': lower_sigma_padded,
    'Upper 2Sigma': upper_2sigma_padded,
    'Lower 2Sigma': lower_2sigma_padded
})


plot_data.to_csv('Am_performance.csv', index=False)

"""### **Uncertainty**"""

# Calculate residuals (errors)
train_residuals = y_train - y_train_pred_ensemble
test_residuals = y_test - y_test_pred_ensemble

# Calculate standard deviations of residuals
train_sigma = np.std(train_residuals)
test_sigma = np.std(test_residuals)

# Calculate ±σ and ±2σ uncertainties
train_uncertainty_sigma = (train_sigma, -train_sigma)
test_uncertainty_sigma = (test_sigma, -test_sigma)

train_uncertainty_2sigma = (2 * train_sigma, -2 * train_sigma)
test_uncertainty_2sigma = (2 * test_sigma, -2 * test_sigma)

# Print the uncertainties
print(f"Training ±σ: +{train_uncertainty_sigma[0]:.4f}, {train_uncertainty_sigma[1]:.4f}")
print(f"Testing ±σ: +{test_uncertainty_sigma[0]:.4f}, {test_uncertainty_sigma[1]:.4f}")
print(f"Training ±2σ: +{train_uncertainty_2sigma[0]:.4f}, {train_uncertainty_2sigma[1]:.4f}")
print(f"Testing ±2σ: +{test_uncertainty_2sigma[0]:.4f}, {test_uncertainty_2sigma[1]:.4f}")

"""### **Feature importance**"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.inspection import PartialDependenceDisplay, partial_dependence

data = pd.read_csv('HTSMA_DATA.csv')
X = data.iloc[:, 1:7]
y = data.iloc[:, 18]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model_definitions = {
    'SVR': Pipeline([
        ('scaler', StandardScaler()),
        ('model', SVR(C=1000, epsilon=1.0, gamma=0.0007665189689585275, kernel='rbf'))
    ]),
    'RandomForest': Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor(bootstrap=True, max_depth=30, min_samples_leaf=1,
                                        min_samples_split=3, n_estimators=300, random_state=42))
    ]),
    'ExtraTrees': Pipeline([
        ('scaler', StandardScaler()),
        ('model', ExtraTreesRegressor(bootstrap=True, max_depth=5, min_samples_leaf=1,
                                      min_samples_split=2, n_estimators=50, random_state=42))
    ]),
    'GaussianProcess': Pipeline([
        ('scaler', StandardScaler()),
        ('model', GaussianProcessRegressor(alpha=0.07653054285055239, n_restarts_optimizer=10))
    ]),
    'KNN': Pipeline([
        ('scaler', StandardScaler()),
        ('model', KNeighborsRegressor(n_neighbors=3, p=1, weights='uniform'))
    ])
}

optimal_weights = [0.2928, 0.0000, 0.7072, 0.0000, 0.0000]
model_names = list(model_definitions.keys())
weights = dict(zip(model_names, optimal_weights))

ensemble_importances = np.zeros(X.shape[1])

for model_name, weight in weights.items():
    if weight > 0:
        model = model_definitions[model_name]
        model.fit(X_train, y_train)


        if hasattr(model.named_steps['model'], 'feature_importances_'):
            model_importances = model.named_steps['model'].feature_importances_
            ensemble_importances += weight * model_importances

ensemble_importances /= sum(weights.values())

feature_importance_df = pd.DataFrame({
    'Feature': X.columns,
    'Importance': ensemble_importances
}).sort_values(by='Importance', ascending=False)

print(feature_importance_df)

#feature_importance_df.to_csv('ensemble_feature_importances.csv', index=False)
plt.figure(figsize=(10, 6))
plt.barh(feature_importance_df['Feature'], feature_importance_df['Importance'])
plt.xlabel('Importance')
plt.ylabel('Features')
plt.title('Feature Importances (Ensemble Model)')
plt.gca().invert_yaxis()
plt.show()

"""### **Composition Vs Am Plot**"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_squared_error, r2_score

model_definitions = {
    'SVR': Pipeline([
        ('scaler', StandardScaler()),
        ('model', SVR(C=1000, epsilon=1.0, gamma=0.0007665189689585275, kernel='rbf'))
    ]),
    'RandomForest': Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor(bootstrap=True, max_depth=30, min_samples_leaf=1,
                                        min_samples_split=3, n_estimators=300, random_state=42))
    ]),
    'ExtraTrees': Pipeline([
        ('scaler', StandardScaler()),
        ('model', ExtraTreesRegressor(bootstrap=True, max_depth=5, min_samples_leaf=1,
                                      min_samples_split=2, n_estimators=50, random_state=42))
    ]),
    'GaussianProcess': Pipeline([
        ('scaler', StandardScaler()),
        ('model', GaussianProcessRegressor(alpha=0.07653054285055239, n_restarts_optimizer=10))
    ]),
    'KNN': Pipeline([
        ('scaler', StandardScaler()),
        ('model', KNeighborsRegressor(n_neighbors=3, p=1, weights='uniform'))
    ])
}

optimal_weights = [0.2928, 0.0000, 0.7072, 0.0000, 0.0000]
svr_weight, rfr_weight, et_weight, gpr_weight, knn_weight = optimal_weights

kf = KFold(n_splits=5, shuffle=True, random_state=42)

y_train_pred_ensemble = np.zeros_like(y_train, dtype=float)
y_test_pred_ensemble = np.zeros_like(y_test, dtype=float)

for train_idx, valid_idx in kf.split(X_train):
    X_train_fold, X_valid_fold = X_train.iloc[train_idx], X_train.iloc[valid_idx]
    y_train_fold, y_valid_fold = y_train.iloc[train_idx], y_train.iloc[valid_idx]

    fold_train_predictions = {}
    fold_test_predictions = {}

    for model_name in ['SVR', 'RandomForest', 'ExtraTrees', 'GaussianProcess', 'KNN']:
        model = model_definitions[model_name]
        model.fit(X_train_fold, y_train_fold)
        fold_train_predictions[model_name] = model.predict(X_valid_fold)
        fold_test_predictions[model_name] = model.predict(X_test)

    fold_train_ensemble = (svr_weight * fold_train_predictions['SVR'] +
                           rfr_weight * fold_train_predictions['RandomForest'] +
                           et_weight * fold_train_predictions['ExtraTrees']+
                           gpr_weight * fold_train_predictions['GaussianProcess']+
                           knn_weight * fold_train_predictions['KNN'])

    fold_test_ensemble = (svr_weight * fold_test_predictions['SVR'] +
                           rfr_weight * fold_test_predictions['RandomForest'] +
                           et_weight * fold_test_predictions['ExtraTrees']+
                           gpr_weight * fold_test_predictions['GaussianProcess']+
                           knn_weight * fold_test_predictions['KNN'])

    y_train_pred_ensemble[valid_idx] = fold_train_ensemble
    y_test_pred_ensemble += fold_test_ensemble / kf.n_splits

def generate_combinations_and_save(columns, filename):
    combinations = []

    for ti in range(1, 101):
        for ni in range(1, 101 - ti):
            third_element = 100 - ni - ti
            if third_element > 0:
                combinations.append([ni, ti, third_element])

    combinations_df = pd.DataFrame(combinations, columns=columns)

    X_custom = pd.DataFrame(0, index=np.arange(len(combinations)), columns=X.columns)
    X_custom['Ni'] = combinations_df['Ni']
    X_custom['Ti'] = combinations_df['Ti']
    X_custom[columns[2]] = combinations_df[columns[2]]

    predicted_temperatures = np.zeros(len(X_custom))
    for model_name, weight in zip(['SVR', 'RandomForest', 'ExtraTrees', 'GaussianProcess', 'KNN'], optimal_weights):
        model = model_definitions[model_name]
        predicted_temperatures += weight * model.predict(X_custom)

    combinations_df['Predicted Temperature'] = predicted_temperatures

    combinations_df.to_csv(filename, index=False)
    print(f"File saved: {filename}")
    print(combinations_df.head())

generate_combinations_and_save(['Ni', 'Ti', 'Zr'], 'Ni_Ti_Zr_combinations.csv')
generate_combinations_and_save(['Ni', 'Ti', 'Hf'], 'Ni_Ti_Hf_combinations.csv')
generate_combinations_and_save(['Ni', 'Ti', 'Pd'], 'Ni_Ti_Pd_combinations.csv')
generate_combinations_and_save(['Ni', 'Ti', 'Pt'], 'Ni_Ti_Pt_combinations.csv')