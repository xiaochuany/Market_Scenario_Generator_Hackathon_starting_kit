from src.evaluation.eval_helper import *
from sklearn.metrics import roc_auc_score


def get_discriminative_score(real_train_dl, real_test_dl, fake_train_dl, fake_test_dl, config):
    mconfig = config.Evaluation.TestMetrics.discriminative_score

    class Discriminator(nn.Module):
        def __init__(self, input_size, hidden_size, num_layers, out_size=2):
            super(Discriminator, self).__init__()
            self.rnn = nn.GRU(input_size=input_size, num_layers=num_layers,
                              hidden_size=hidden_size, batch_first=True)
            self.linear = nn.Linear(hidden_size, out_size)

        def forward(self, x):
            x = self.rnn(x)[0][:, -1]
            return self.linear(x)

    train_dl = create_dl(real_train_dl, fake_train_dl, mconfig.batch_size, cutoff=False)
    test_dl = create_dl(real_test_dl, fake_test_dl, mconfig.batch_size, cutoff=False)

    pm = TrainValidateTestModel(epochs=mconfig.epochs, device=config.device)
    test_acc_list = []
    for i in range(1):
        model = Discriminator(train_dl.dataset[0][0].shape[-1], mconfig.hidden_size, mconfig.num_layers)
        _, _, test_acc = pm.train_val_test_classification(train_dl, test_dl, model, train=True, validate=True)
        test_acc_list.append(test_acc)
    mean_acc = np.mean(np.array(test_acc_list))
    std_acc = np.std(np.array(test_acc_list))
    return abs(mean_acc - 0.5), std_acc


def get_predictive_score(real_train_dl, real_test_dl, fake_train_dl, fake_test_dl, config):
    mconfig = config.Evaluation.TestMetrics.predictive_score

    train_dl = create_dl(fake_train_dl, fake_test_dl, mconfig.batch_size, cutoff=True)
    test_dl = create_dl(real_train_dl, real_test_dl, mconfig.batch_size, cutoff=True)

    class Predictor(nn.Module):
        def __init__(self, input_size, hidden_size, num_layers, out_size):
            super(Predictor, self).__init__()
            self.rnn = nn.LSTM(input_size=input_size, num_layers=num_layers,
                               hidden_size=hidden_size, batch_first=True)
            self.linear = nn.Linear(hidden_size, out_size)

        def forward(self, x):
            x = self.rnn(x)[0][:, -1]
            return self.linear(x)

    pm = TrainValidateTestModel(epochs=mconfig.epochs, device=config.device)
    test_loss_list = []
    for i in range(1):  ## Question: WHY 1?
        model = Predictor(train_dl.dataset[0][0].shape[-1],
                          mconfig.hidden_size,
                          mconfig.num_layers,
                          out_size=train_dl.dataset[0][1].shape[-1]
                          )
        model, test_loss = pm.train_val_test_regressor(
            train_dl=train_dl,
            test_dl=test_dl,
            model=model,
            train=True,
            validate=True
        )
        test_loss_list.append(test_loss)
    mean_loss = np.mean(np.array(test_loss_list))
    std_loss = np.std(np.array(test_loss_list))
    return mean_loss, std_loss


def get_classification_score(real_train_dl, real_test_dl, fake_train_dl, fake_test_dl, config):
    mconfig = config.Evaluation.TestMetrics.discriminative_score

    class Discriminator(nn.Module):
        def __init__(self, input_size, hidden_size, num_layers, out_size=2):
            super(Discriminator, self).__init__()
            self.rnn = nn.GRU(input_size=input_size, num_layers=num_layers,
                              hidden_size=hidden_size, batch_first=True)
            self.linear = nn.Linear(hidden_size, out_size)

        def forward(self, x):
            x = self.rnn(x)[0][:, -1]
            return self.linear(x).softmax(dim=1)

    train_dl = create_dl(real_train_dl, fake_train_dl, mconfig.batch_size, cutoff=False)
    test_dl = create_dl(real_test_dl, fake_test_dl, mconfig.batch_size, cutoff=False)

    pm = TrainValidateTestModel(epochs=mconfig.epochs, device=config.device)
    test_acc_list = []
    for i in range(1):
        model = Discriminator(train_dl.dataset[0][0].shape[-1], mconfig.hidden_size, mconfig.num_layers)
        _, test_labels, test_acc = pm.train_val_test_classification(train_dl, test_dl, model, train=True, validate=True)
        test_acc_list.append(test_acc)
    return test_labels


def compute_auc(truth_crisis, fake_crisis, truth_regular, fake_regular, config):
    crisis_training_set = torch.cat([truth_crisis[:truth_crisis.shape[0] // 2], fake_crisis])[:200]
    regular_training_set = truth_regular[:200]

    crisis_training_dl = DataLoader(TensorDataset(crisis_training_set), batch_size=32, shuffle=True)
    regular_training_dl = DataLoader(TensorDataset(truth_regular[:200]), batch_size=32, shuffle=True)

    crisis_test_dl = DataLoader(TensorDataset(truth_crisis[truth_crisis.shape[0] // 2:]), batch_size=4, shuffle=True)
    regular_test_dl = DataLoader(TensorDataset(truth_regular[200:216]), batch_size=4, shuffle=True)

    true_labels, pred_labels = get_classification_score(crisis_training_dl, crisis_test_dl, regular_training_dl,
                                                        regular_test_dl, config)

    # print(true_labels, pred_labels)
    auc = roc_auc_score(true_labels[0].cpu().numpy(), pred_labels[0].cpu().numpy())

    return auc